import os
import requests
import hashlib
import hmac
import json
import uuid
import threading
import time
from fastapi import FastAPI, Request, HTTPException, Header
import uvicorn

# ==========================================
# 1. CONFIGURATION & SECRETS
# ==========================================
ATF_ENDPOINT = os.getenv("ATF_API_URL", "https://latrivex.com/api/v1/atf")

# SHARED SECRET: Used to sign and verify webhooks. 
# In production, pass this via environment variable (e.g., os.getenv("ATF_WEBHOOK_SECRET"))
WEBHOOK_SECRET = os.getenv("ATF_WEBHOOK_SECRET", "latrivex_sec_key_998234719283749")

PENDING_TRANSACTIONS = {}

# ==========================================
# 2. ATF INTERCEPTOR CLASS
# ==========================================
class LATRIVEX_ATF_Interceptor:
    def __init__(self, agent_name: str, framework: str):
        self.default_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) LATRIVEX-Agent-SDK/1.0",
            "Accept": "application/json"
        }
        try:
            reg_res = requests.post(
                f"{ATF_ENDPOINT}/agents/register", 
                json={"agentName": agent_name, "framework": framework, "owner": "Autonomous FinTech Operations"},
                headers=self.default_headers
            )
            reg_res.raise_for_status() 
            data = reg_res.json()
            self.agent_id = data["registeredEntity"]["id"]
            self.token = data["registeredEntity"]["attestationToken"]
        except Exception:
            self.agent_id = f"spiffe://latrivex.atf/agent/langgraph/{uuid.uuid4().hex[:8]}"
            self.token = "mock_token"

    def evaluate_action(self, action_context: str, target_asset: str, risk_factor: int):
        payload = {"actionContext": action_context, "targetAsset": target_asset, "riskScore": risk_factor}
        payload_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')
        payload_hash = hashlib.sha256(payload_bytes).hexdigest()
        
        headers = {
            "X-ATF-Agent-ID": self.agent_id,
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) LATRIVEX-Agent-SDK/1.0",
            "X-ATF-Payload-Hash": f"sha256={payload_hash}",
            "X-ATF-Signature-Mode": "Enforced"
        }
        
        try:
            eval_res = requests.post(f"{ATF_ENDPOINT}/evaluate", json=payload, headers=headers)
            eval_res.raise_for_status()
            data = eval_res.json()
            return data["evaluation"]["verdict"], data["evaluation"]["evidenceLedger"]["blockHash"]
        except Exception:
            verdict = "ALLOW" if risk_factor < 40 else "REQUIRE_HUMAN_APPROVAL" if risk_factor < 75 else "QUARANTINE"
            return verdict, "0x" + uuid.uuid4().hex[:12]

atf_guard = LATRIVEX_ATF_Interceptor("Treasury AI", "langgraph")

# ==========================================
# 3. CORE AGENT LOGIC
# ==========================================
def execute_agent_transfer(amount: float, recipient: str):
    risk_factor = 15 if amount <= 100000 else 55
    action_desc = f"Routing {int(amount)} USD to destination {recipient.replace('-', '')}"
    tx_id = f"TX-{uuid.uuid4().hex[:8].upper()}"
    
    print(f"\n-> Agent attempting action: '{action_desc}' (Risk: {risk_factor})")
    verdict, proof_hash = atf_guard.evaluate_action(action_desc, "Payment_Gateway", risk_factor)
    
    if verdict == "ALLOW":
        print(f"   [L6 Decision]: ✅ {verdict}")
        print(f"   [EXECUTION]: 💸 Wire {tx_id} executed successfully.")
        
    elif verdict == "REQUIRE_HUMAN_APPROVAL":
        print(f"   [L6 Decision]: ⚠️ {verdict} (Proof: {proof_hash})")
        PENDING_TRANSACTIONS[tx_id] = {
            "amount": amount,
            "recipient": recipient,
            "proof_hash": proof_hash
        }
        print(f"   [EXECUTION]: ⏸️ Transaction {tx_id} parked. Waiting for signed webhook...")
        return tx_id
        
    else:
        print(f"   [L6 Decision]: 🚨 QUARANTINE")
        print(f"   [EXECUTION]: ⛔ Action BLOCKED.")
    
    return None

def finalize_approved_transfer(tx_id: str):
    if tx_id in PENDING_TRANSACTIONS:
        tx = PENDING_TRANSACTIONS.pop(tx_id)
        print(f"\n   [SECURE WEBHOOK VERIFIED]: Valid signature received for {tx_id}!")
        print(f"   [EXECUTION RESUMED]: 💸 Routing {tx['amount']} USD to {tx['recipient']}. (Anchored to {tx['proof_hash']})")
    else:
        print(f"\n   [WARNING]: Received approval for unknown or expired transaction ID: {tx_id}")

# ==========================================
# 4. SECURED WEBHOOK LISTENER (FastAPI)
# ==========================================
app = FastAPI(title="Secured Agent Webhook Listener")

@app.post("/webhook/atf-approval")
async def receive_human_approval(
    request: Request,
    x_atf_signature: str = Header(None, alias="X-ATF-Signature")
):
    # STEP 1: Ensure signature header exists
    if not x_atf_signature:
        print("\n   [SECURITY ALERT]: Webhook rejected! Missing X-ATF-Signature header.")
        raise HTTPException(status_code=401, detail="Missing signature header")
    
    # STEP 2: Read raw byte payload (Must use raw bytes for HMAC validation)
    body_bytes = await request.body()
    
    # STEP 3: Compute expected HMAC SHA-256 signature using the shared secret
    expected_hash = hmac.new(
        WEBHOOK_SECRET.encode('utf-8'),
        body_bytes,
        hashlib.sha256
    ).hexdigest()
    
    expected_sig = f"sha256={expected_hash}"
    
    # STEP 4: Constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(expected_sig, x_atf_signature):
        print(f"\n   [SECURITY ALERT]: Webhook rejected! Signature mismatch.")
        print(f"   [RECEIVED]: {x_atf_signature}")
        print(f"   [EXPECTED]: {expected_sig}")
        raise HTTPException(status_code=403, detail="Invalid signature")

    # STEP 5: Process payload once verification succeeds
    payload = await request.json()
    tx_id = payload.get("transaction_id")
    action = payload.get("action")
    
    if action == "APPROVED":
        finalize_approved_transfer(tx_id)
        return {"status": "success", "message": f"Transaction {tx_id} verified and resumed."}
    else:
        print(f"\n   [SECURE WEBHOOK VERIFIED]: Human REJECTED transaction {tx_id}.")
        PENDING_TRANSACTIONS.pop(tx_id, None)
        return {"status": "success", "message": "Transaction aborted."}

def run_webhook_server():
    import logging
    log = logging.getLogger("uvicorn.error")
    log.setLevel(logging.CRITICAL)
    uvicorn.run(app, host="127.0.0.1", port=5005)

# ==========================================
# 5. HELPER FUNCTION: SIGN WEBHOOK PAYLOADS
# ==========================================
def send_signed_webhook(payload: dict):
    """Simulates how the LATRIVEX Backend generates and sends signed webhooks."""
    body_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    sig_hash = hmac.new(WEBHOOK_SECRET.encode('utf-8'), body_bytes, hashlib.sha256).hexdigest()
    
    headers = {
        "Content-Type": "application/json",
        "X-ATF-Signature": f"sha256={sig_hash}"
    }
    
    return requests.post("http://127.0.0.1:5005/webhook/atf-approval", data=body_bytes, headers=headers)

# ==========================================
# 6. DEMO RUNNER
# ==========================================
if __name__ == "__main__":
    print("[SYSTEM] Starting Secured Webhook Listener on port 5005...")
    threading.Thread(target=run_webhook_server, daemon=True).start()
    time.sleep(1)
    
    # 1. Trigger High-Value Transfer
    paused_tx_id = execute_agent_transfer(250000.0, "Partner Bank AC882")
    
    if paused_tx_id:
        time.sleep(2)
        
        print("\n--- TEST 1: Attacker sends an unsigned fake POST request ---")
        try:
            fake_res = requests.post(
                "http://127.0.0.1:5005/webhook/atf-approval", 
                json={"transaction_id": paused_tx_id, "action": "APPROVED"}
            )
            print(f"   [ATTACK RESULT]: HTTP {fake_res.status_code} - {fake_res.json()['detail']}")
        except Exception as e:
            pass
            
        time.sleep(2)
        
        print("\n--- TEST 2: Attacker sends a forged/incorrect signature ---")
        try:
            bad_sig_res = requests.post(
                "http://127.0.0.1:5005/webhook/atf-approval", 
                json={"transaction_id": paused_tx_id, "action": "APPROVED"},
                headers={"X-ATF-Signature": "sha256=invalid_hash_12345"}
            )
            print(f"   [ATTACK RESULT]: HTTP {bad_sig_res.status_code} - {bad_sig_res.json()['detail']}")
        except Exception as e:
            pass
            
        time.sleep(2)
        
        print("\n--- TEST 3: LATRIVEX sends legitimate signed approval ---")
        send_signed_webhook({"transaction_id": paused_tx_id, "action": "APPROVED"})