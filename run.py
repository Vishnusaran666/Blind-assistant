"""
Start the Blind Assist server and print the address to open on your phone.

  python run.py                 # plain HTTP (works for testing on this computer only)
  python run.py --https         # HTTPS with a self-signed certificate (phone on same Wi-Fi)

WHY HTTPS? Phone browsers only allow the camera and microphone on https:// pages
(or on localhost). Easiest alternatives to --https are a tunnel such as
`cloudflared tunnel --url http://localhost:8000` or `ngrok http 8000`,
which give you a proper https:// address. See README.md.
"""

import argparse
import shutil
import socket
import subprocess
import sys
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parent
CERT_DIR = ROOT / "certs"


def lan_ip():
    """The address your phone can reach this computer on (same Wi-Fi)."""
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("10.255.255.255", 1))     # nothing is sent; just picks the right network card
        return probe.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        probe.close()


def make_self_signed_cert(ip):
    CERT_DIR.mkdir(exist_ok=True)
    key, cert = CERT_DIR / "key.pem", CERT_DIR / "cert.pem"
    if key.exists() and cert.exists():
        return key, cert
    if not shutil.which("openssl"):
        sys.exit("openssl not found. Install it, or use a tunnel (cloudflared / ngrok) instead.")
    subprocess.run([
        "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
        "-keyout", str(key), "-out", str(cert), "-days", "365",
        "-subj", "/CN=blind-assist", "-addext", f"subjectAltName=IP:{ip},DNS:localhost",
    ], check=True)
    return key, cert


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--https", action="store_true", help="serve HTTPS with a self-signed certificate")
    args = parser.parse_args()

    ip = lan_ip()
    kwargs = {}
    scheme = "http"
    if args.https:
        key, cert = make_self_signed_cert(ip)
        kwargs = {"ssl_keyfile": str(key), "ssl_certfile": str(cert)}
        scheme = "https"

    print("\n" + "=" * 60)
    print(f" On this computer : {scheme}://localhost:{args.port}")
    print(f" On your phone    : {scheme}://{ip}:{args.port}   (same Wi-Fi)")
    if args.https:
        print(" The phone will warn about the certificate: tap Advanced > Continue.")
    else:
        print(" Phone camera needs HTTPS: use --https or a tunnel (see README).")
    print("=" * 60 + "\n")

    uvicorn.run("backend.main:app", host="0.0.0.0", port=args.port, **kwargs)


if __name__ == "__main__":
    main()
