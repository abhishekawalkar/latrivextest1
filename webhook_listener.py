# webhook_listener.py
import os
import hmac
import hashlib
from fastapi import FastAPI, Request, HTTPException, Header
import uvicorn

app = FastAPI(title="LATRIVEX Webhook Listener")
WEBHOOK_SECRET = os.getenv("ATF_WEBHOOK_SECRET", "latrivex_sec_key_998234719283749")

# Shared state or database lookup function
def complete_transaction(tx_id: str):
    print(f"\n[SUCCESS] Transaction {tx_id} approved and resumed!")

@app.post("/webhook/atf-approval")
async def receive_human_approval(
    request: Request,
    x_atf_signature: str = Header(None, alias="X-ATF-Signature")
):
    if not x_atf_signature:
        raise HTTPException(status_code=401, detail="Missing signature header")
    
    body_bytes = await request.body()
    expected_hash = hmac.new(WEBHOOK_SECRET.encode('utf-8'), body_bytes, hashlib.sha256).hexdigest()
    
    if not hmac.compare_digest(f"sha256={expected_hash}", x_atf_signature):
        raise HTTPException(status_code=403, detail="Invalid signature")

    payload = await request.json()
    tx_id = payload.get("transaction_id")
    action = payload.get("action")
    
    if action == "APPROVED":
        complete_transaction(tx_id)
        return {"status": "success", "message": f"Transaction {tx_id} executed."}
    
    return {"status": "aborted", "message": "Transaction rejected."}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5005)