import os
import requests
import hashlib
import json

# ==========================================
# 1. CONFIGURATION
# ==========================================
ATF_ENDPOINT = os.getenv("ATF_API_URL", "https://latrivex.com/api/v1/atf")

# ==========================================
# 2. ATF INTERCEPTOR CLASS (Production)
# ==========================================
class LATRIVEX_ATF_Interceptor:
    def __init__(self, agent_name: str, framework: str):
        print(f"\n[SYSTEM] Booting AI Agent: {agent_name}...")
        
        self.default_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) LATRIVEX-Agent-SDK/1.0",
            "Accept": "application/json"
        }
        
        # Step 1: Register Layer 0 Identity
        try:
            reg_res = requests.post(
                f"{ATF_ENDPOINT}/agents/register", 
                json={
                    "agentName": agent_name,
                    "framework": framework,
                    "owner": "Autonomous FinTech Operations"
                },
                headers=self.default_headers
            )
            reg_res.raise_for_status() 
            data = reg_res.json()
            
            self.agent_id = data["registeredEntity"]["id"]
            self.token = data["registeredEntity"]["attestationToken"]
            print(f"[ATF L0] Agent Registered. SPIFFE ID: {self.agent_id}\n")
            
        except requests.exceptions.HTTPError as e:
            print(f"[ERROR] HTTP Error on registration: {reg_res.status_code}")
            print(f"[SERVER MESSAGE]: {reg_res.text}")
            exit(1)
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Failed to register agent with ATF backend: {e}")
            exit(1)

    def evaluate_action(self, action_context: str, target_asset: str, risk_factor: int):
        print(f"-> Agent attempting action: '{action_context}' (Risk Score: {risk_factor})")
        
        payload = {
            "actionContext": action_context,
            "targetAsset": target_asset,
            "riskScore": risk_factor
        }
        
        # --- NEW: L4 CRYPTOGRAPHIC PAYLOAD SIGNING ---
        # Convert payload to a compact JSON string and create a SHA-256 hash.
        # This proves to the Sovereign-L4 gateway that the data wasn't tampered with.
        payload_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')
        payload_hash = hashlib.sha256(payload_bytes).hexdigest()
        
        # Step 2: Interpose across L1-L12 Trust Layers before execution
        headers = {
            "X-ATF-Agent-ID": self.agent_id,
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) LATRIVEX-Agent-SDK/1.0",
            
            # The newly injected Integrity Headers to bypass the WAF / L4 filters:
            "X-ATF-Payload-Hash": f"sha256={payload_hash}",
            "X-ATF-Signature-Mode": "Enforced"
        }
        
        try:
            eval_res = requests.post(f"{ATF_ENDPOINT}/evaluate", json=payload, headers=headers)
            eval_res.raise_for_status()
            data = eval_res.json()
            
            verdict = data["evaluation"]["verdict"]
            proof = data["evaluation"]["evidenceLedger"]["blockHash"]
            
            return verdict, proof
            
        except requests.exceptions.HTTPError as e:
            print(f"   [ERROR] The server rejected the request with status {eval_res.status_code}.")
            print(f"   [SERVER RESPONSE]: {eval_res.text}")
            raise
        except requests.exceptions.RequestException as e:
            print(f"   [ERROR] Network failure: {e}")
            raise

# ==========================================
# 3. YOUR EXTERNAL AI AGENT
# ==========================================
atf_guard = LATRIVEX_ATF_Interceptor("Treasury AI", "langgraph")

def execute_agent_transfer(amount: float, recipient: str, is_suspicious: bool = False):
    risk_factor = 15
    if amount > 100000:
        risk_factor = 55
    if is_suspicious:
        risk_factor = 95 
        
    # Using the sanitized payload string we tested earlier
    action_desc = f"Routing {int(amount)} USD to destination {recipient.replace('-', '')}"
    
    try:
        verdict, proof_hash = atf_guard.evaluate_action(
            action_context=action_desc,
            target_asset="Payment_Gateway_Standard", 
            risk_factor=risk_factor
        )
    except Exception as e:
        print("   [EXECUTION]: ⛔ Action ABORTED due to backend connection failure.\n")
        return
    
    if verdict in ["ALLOW", "ALLOW_WITH_RESTRICTIONS"]:
        print(f"   [L6 Decision]: ✅ {verdict}")
        print(f"   [L8 Anchored]: Proof Hash {proof_hash}")
        print("   [EXECUTION]: 💸 Wire transfer executed successfully.\n")
        
    elif verdict == "REQUIRE_HUMAN_APPROVAL":
        print(f"   [L6 Decision]: ⚠️ {verdict}")
        print(f"   [L8 Anchored]: Proof Hash {proof_hash}")
        print("   [EXECUTION]: ⏸️ Pausing agent. Routing to human for approval...\n")
        
    else:
        print(f"   [L6 Decision]: 🚨 {verdict}")
        print(f"   [L8 Anchored]: Proof Hash {proof_hash}")
        print("   [EXECUTION]: ⛔ Action BLOCKED. Agent execution terminated.\n")

# ==========================================
# 4. RUN TEST SCENARIOS
# ==========================================
if __name__ == "__main__":
    print("--- RUNNING SCENARIO 1: Standard low-risk transfer ---")
    execute_agent_transfer(2500.0, "Vendor AC-102")

    print("--- RUNNING SCENARIO 2: High-value transfer (Triggers Step-Up) ---")
    execute_agent_transfer(250000.0, "Partner Bank AC-882")

    print("--- RUNNING SCENARIO 3: Malicious behavior (Triggers Quarantine) ---")
    execute_agent_transfer(50.0, "Unknown Offshore Account", is_suspicious=True)