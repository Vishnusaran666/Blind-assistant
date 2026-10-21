# Blind Assist - mobile app (frontend + backend)

A phone app that uses the camera to tell a blind person **what is around them, on which side, and roughly how far**, and that they can **talk to** in English or Tamil.

```
 PHONE (browser app = frontend)                      SERVER (Python = backend)
 ------------------------------                      -------------------------
 camera ──► frame (JPEG) ───── POST /detect ───────► FastAPI ──► YOLOv8
                                                                    │
 speaks  ◄── sentence ◄── logic.js ◄── JSON objects ◄───────────────┘
 listens ──► text ──► command ──► answer            (what, left/front/right, distance)
        └── unknown question ── POST /ask ────────► Claude (optional, key stays on server)
```

Why this design? Phones cannot easily run Python, so the heavy part (YOLO) runs on a computer or cloud server, and the phone does what it is best at: camera, microphone and speaker. The phone page can be added to the home screen like an app.

## Folder map

| File | What it does |
| --- | --- |
| `backend/main.py` | FastAPI server. Loads YOLOv8, `POST /detect` (image in, objects out), `POST /ask`, `GET /health`, also serves the phone page |
| `run.py` | Starts the server and prints the address to open on the phone |
| `frontend/index.html`, `style.css` | The screen: big high-contrast buttons |
| `frontend/logic.js` | The "brain": sentences in English/Tamil, command understanding, when to speak, false-alarm filter |
| `frontend/app.js` | Phone plumbing: camera, calls to the server, voice in and out |
| `frontend/manifest.json`, icons | Lets you "Add to Home screen" |

## 1. Set up the server (once)

Python 3.9 or newer.

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r backend/requirements.txt
```

The first start downloads `yolov8n.pt` (about 6 MB), so it needs internet once.

## 2. Run it

```bash
python run.py
```

It prints the addresses. **Phone browsers only allow camera and microphone on `https://` pages**, so pick one way to get HTTPS:

**A. Tunnel (easiest, also works away from home Wi-Fi)**
Install [cloudflared](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/) (or ngrok), then in a second terminal:

```bash
cloudflared tunnel --url http://localhost:8000     # or: ngrok http 8000
```

Open the `https://...` address it prints, on your phone.

**B. Same Wi-Fi, self-signed certificate**

```bash
python run.py --https
```

Open `https://<the IP it prints>:8000` on the phone, tap *Advanced > Continue* on the certificate warning.

**Protect it.** A tunnel address is public. Set a password token and open the page once with it:

```bash
ACCESS_TOKEN=mysecret python run.py                # Windows PowerShell: $env:ACCESS_TOKEN="mysecret"
# phone, first time only:  https://xxxx.trycloudflare.com/?token=mysecret
```

**Optional free-form answers from Claude:** set `ANTHROPIC_API_KEY` on the server before `python run.py`. The key stays on the server, never on the phone.

## 3. Use it (Android Chrome works best)

1. Open the page, tap **Start**, allow the camera.
2. Tap **Ask**, then speak: "what is in front of me", "is there a chair", "how many people", "nearest", "help".
3. Buttons do the same without speaking. **Talk** = also announce new objects now and then. **Quiet** = only warnings (default).
4. It warns ("Careful. person, about 1 meter, in front of you") and vibrates when a known object is closer than about 1.2 m straight ahead.
5. தமிழ் button switches voice, commands and sentences to Tamil.

**Tamil voice:** the phone must have a Tamil voice. Android: Settings > Languages > Text-to-speech > Google > Install voice data > Tamil. The app shows a notice if none is found.

## 4. Make the distance right (important)

Distance is estimated from the box width, so it needs your phone's camera setting:

1. Stand a person exactly 1 metre from the phone.
2. Look at the distance in the box label on screen.
3. New `FOCAL_RATIO` = old value x (true distance / shown distance). Default is `0.8`. If it shows 2 m for 1 m, use `0.4`.
4. Restart with `FOCAL_RATIO=0.4 python run.py`.

Settings you can change with environment variables: `FOCAL_RATIO`, `CONFIDENCE` (default 0.6; higher = fewer false objects), `IMGSZ` (default 416; smaller = faster), `MODEL_PATH`, `ACCESS_TOKEN`, `ANTHROPIC_API_KEY`.

## 5. How the false alarms and the nagging are reduced

- Only 32 useful object types are reported (no "toothbrush" or "kite").
- An object must appear in 2 responses in a row before it counts (`Stabilizer` in `logic.js`).
- Objects whose real size we do not know are named **without** a distance, and never trigger a warning.
- Quiet by default. Warnings are rate-limited; updates (Talk mode) only for new objects, never while it is still speaking.

## 6. Running the model on the phone itself (next step)

Right now the phone needs a network connection to the server. To remove that, export the model and run it in the browser:

```bash
yolo export model=yolov8n.pt format=onnx      # then use onnxruntime-web in app.js
```

`logic.js` stays unchanged. Only the `fetch("/detect")` call in `app.js` is replaced by local inference. It is slower on a phone CPU and needs more work (image pre-processing and box decoding), so start with this server version.

## 7. Deploy so you do not need your laptop

Any small Linux server or container host that runs Python works (a CPU is enough, about 50-150 ms per frame). Run `python run.py` behind HTTPS and set `ACCESS_TOKEN`.

## Limits and safety

- It knows only the YOLO classes in the list: **not stairs, doors, kerbs, potholes or traffic.** Fine-tune a custom model to add them.
- Distances are rough (often +/- 30 percent). Dark scenes and shaky cameras give poor results.
- It is an aid, **not a replacement for a cane, a guide dog or a person**. It never says a path is safe.
- Speech recognition (Chrome) and the Tamil voice may send audio or text to Google or the phone maker's online service. Camera frames go to your own server.

## Troubleshooting

| Problem | Fix |
| --- | --- |
| "The camera needs a secure page" | Open the `https://` address (tunnel or `--https`), not `http://` |
| Page opens but "Server not reachable" | Same Wi-Fi? Firewall allowing port 8000? Tunnel still running? |
| No sound | Turn up the phone media volume; tap Start first (browsers need a tap before speaking) |
| Tamil sounds wrong or silent | Install the Tamil voice (section 3) |
| Ask button missing | Voice input needs Chrome on Android; the buttons still work |
| 401 errors | Open the page once with `?token=...` |
| Slow | Lower `IMGSZ` (320), use a nearer or faster server |
