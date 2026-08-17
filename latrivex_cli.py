import argparse
import hmac
import hashlib
import json
import requests
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("LATRIVEX_SECRET_KEY", "latrivex_sec_key_998234719283749")

def approve_transaction(url: str, tx_id: str, action: str):
    payload = {"tx_id": tx_id, "action": action}
    payload_bytes = json.dumps(payload).encode('utf-8')
    sig = hmac.new(SECRET_KEY.encode('utf-8'), payload_bytes, hashlib.sha256).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "X-ATF-Signature": sig
    }

    print(f"\n[CLI] Transmitting HMAC-Signed Approval to: {url}")
    print(f"[CLI] Generated HMAC Signature: {sig}")

    try:
        res = requests.post(url, data=payload_bytes, headers=headers)
        print(f"[CLI Response {res.status_code}]: {res.text}")
    except Exception as e:
        print(f"[CLI Error]: Connection failed - {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LATRIVEX CLI Tool")
    subparsers = parser.add_subparsers(dest="command")

    approve_p = subparsers.add_parser("approve", help="Send L10 Step-up Webhook Approval")
    approve_p.add_argument("--url", required=True, help="Active Ngrok Webhook URL")
    approve_p.add_argument("--tx-id", required=True, help="Transaction ID")
    approve_p.add_argument("--action", default="APPROVED", choices=["APPROVED", "REJECTED"])

    args = parser.parse_args()

    if args.command == "approve":
        approve_transaction(args.url, args.tx_id, args.action)
    else:
        parser.print_help()