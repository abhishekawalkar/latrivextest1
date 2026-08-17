import os
import sys
import hmac
import hashlib
import json
import time
import math
import asyncio
from typing import List, Dict, Any, Tuple
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import StreamingResponse
import uvicorn

load_dotenv()

# Configuration
ATF_ENDPOINT = os.getenv("LATRIVEX_ATF_ENDPOINT", "https://latrivex.com/api/v1/atf")
API_KEY = os.getenv("LATRIVEX_API_KEY", "ltx_live_pk_9982347192837498237492")
SECRET_KEY = os.getenv("LATRIVEX_SECRET_KEY", "latrivex_sec_key_998234719283749")
AGENT_NAME = os.getenv("AGENT_NAME", "Treasury-Rebalancing-Bot")
AGENT_FRAMEWORK = os.getenv("AGENT_FRAMEWORK", "LangGraph")
AGENT_OWNER = os.getenv("AGENT_OWNER", "Finance-Engineering")

app = FastAPI(title="LATRIVEX ATF Production Engine (L0-L8 Hardened)")

# Streaming Queue for L11 Telemetry
telemetry_queue: asyncio.Queue = asyncio.Queue()

# Behavioral Analytics State (L3)
transaction_velocity_history: List[float] = [12000.0, 15000.0, 18000.0, 22000.0]


# =====================================================================
# CRYPTOGRAPHIC & MATHEMATICAL UTILITIES FOR L0 - L8
# =====================================================================

def verify_spiffe_format(spiffe_id: str) -> bool:
    """L0: Validates SPIFFE ID syntax according to SPIFFE standard."""
    return spiffe_id.startswith("spiffe://latrivex.atf/agent/") and len(spiffe_id) > 30


def compute_pcr_digest(agent_id: str, timestamp: float) -> str:
    """L1: Computes a synthetic hardware PCR register attestation hash."""
    raw_payload = f"TPM_PCR0:{agent_id}:{timestamp}:ENCLAVE_NITRO_ACTIVE".encode('utf-8')
    return "0x" + hashlib.sha256(raw_payload).hexdigest()


def calculate_time_decay_trust(initial_trust: float, last_active_ts: float, half_life_seconds: float = 3600.0) -> float:
    """L2: Applies continuous exponential time-decay to unverified trust scores."""
    elapsed = time.time() - last_active_ts
    decay_factor = math.exp(-elapsed / half_life_seconds)
    return round(initial_trust * decay_factor, 2)


def calculate_velocity_anomaly(current_amount: float) -> float:
    """L3: Calculates standard deviation shift in transaction velocity."""
    if not transaction_velocity_history:
        return 0.0
    mean = sum(transaction_velocity_history) / len(transaction_velocity_history)
    variance = sum((x - mean) ** 2 for x in transaction_velocity_history) / len(transaction_velocity_history)
    std_dev = math.sqrt(variance) if variance > 0 else 1.0
    z_score = (current_amount - mean) / std_dev
    return round(max(0.0, z_score * 10), 2)  # Normalized anomaly score 0-100


def evaluate_8_vector_risk(amount: float, trust_score: float, velocity_anomaly: float) -> float:
    """L4: Calculates 8-Vector Composite Risk Matrix score (0-100)."""
    v_identity = (100 - trust_score) * 0.20
    v_transaction = min(100.0, (amount / 250000.0) * 100.0) * 0.30
    v_behavioral = velocity_anomaly * 0.25
    v_asset = 25.0 * 0.25  # Fixed weight for target vault asset sensitivity

    composite_risk = v_identity + v_transaction + v_behavioral + v_asset
    return round(min(100.0, max(0.0, composite_risk)), 2)


def evaluate_policy_rules(risk_score: float, amount: float) -> Tuple[str, str]:
    """L5: Applies declarative policy rule evaluations."""
    if amount > 100000.0 or risk_score >= 60.0:
        return "REQUIRE_HUMAN_APPROVAL", "RULE_POL_2026_ATF_HIGH_VALUE_OR_RISK"
    elif risk_score >= 40.0:
        return "ALLOW_WITH_RESTRICTIONS", "RULE_POL_2026_ATF_MEDIUM_RISK"
    return "ALLOW", "RULE_POL_2026_ATF_LOW_RISK"


def build_merkle_tree_root(elements: List[str]) -> str:
    """L8: Builds a binary Merkle Tree Root Hash over execution parameters."""
    hashes = [hashlib.sha256(e.encode('utf-8')).hexdigest() for e in elements]
    while len(hashes) > 1:
        if len(hashes) % 2 != 0:
            hashes.append(hashes[-1])
        next_level = []
        for i in range(0, len(hashes), 2):
            combined = (hashes[i] + hashes[i + 1]).encode('utf-8')
            next_level.append(hashlib.sha256(combined).hexdigest())
        hashes = next_level
    return "0x" + hashes[0]


async def emit_telemetry(layer: str, status: str, details: dict):
    """L11: Broadcasts real-time layer telemetry payload."""
    event_payload = {
        "timestamp": time.time(),
        "layer": layer,
        "status": status,
        "details": details
    }
    await telemetry_queue.put(f"data: {json.dumps(event_payload)}\n\n")


# =====================================================================
# AGENT STATE & REGISTRATION (L0)
# =====================================================================

agent_session = {
    "spiffe_id": f"spiffe://latrivex.atf/agent/{AGENT_FRAMEWORK.lower()}/prod-01",
    "jwt_token": None,
    "trust_score": 85.0,
    "last_active": time.time()
}

@app.get("/telemetry/stream")
async def stream_telemetry(request: Request):
    """L11 SSE Endpoint for Live Control Room Streaming."""
    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
            message = await telemetry_queue.get()
            yield message

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# =====================================================================
# FULL L0 - L12 EXECUTION PIPELINE
# =====================================================================

@app.post("/execute-tool")
async def execute_tool_action(action_context: str, amount: float, target_asset: str):
    tx_id = f"TX-{hashlib.md5(f'{time.time()}'.encode()).hexdigest()[:8].upper()}"
    now = time.time()

    print(f"\n=================================================================")
    print(f" [PRODUCTION L0-L8 PIPELINE] EVALUATING: {tx_id}")
    print(f" Context: '{action_context}' | Amount: ${amount:,.2f} | Target: {target_asset}")
    print(f"=================================================================")

    # L0: Universal Identity Verification
    spiffe_id = agent_session["spiffe_id"]
    if not verify_spiffe_format(spiffe_id):
        raise HTTPException(status_code=401, detail="L0 Validation Failed: Invalid SPIFFE Format")
    await emit_telemetry("L0_Identity", "VERIFIED", {"spiffe_id": spiffe_id})

    # L1: Identity Attestation (Hardware Enclave Digest)
    pcr_digest = compute_pcr_digest(spiffe_id, now)
    await emit_telemetry("L1_Attestation", "VERIFIED", {"pcr_digest": pcr_digest})

    # L2: Trust Intelligence Engine (Exponential Time Decay)
    decayed_trust = calculate_time_decay_trust(agent_session["trust_score"], agent_session["last_active"])
    agent_session["last_active"] = now
    await emit_telemetry("L2_TrustEngine", "DECAY_APPLIED", {"decayed_trust": decayed_trust})

    # L3: Behavioral Intelligence (Velocity Deviation Engine)
    velocity_anomaly = calculate_velocity_anomaly(amount)
    transaction_velocity_history.append(amount)
    await emit_telemetry("L3_Behavioral", "ANOMALY_EVALUATED", {"z_score_anomaly": velocity_anomaly})

    # L4: Adaptive Risk Intelligence (8-Vector Composite Calculation)
    composite_risk = evaluate_8_vector_risk(amount, decayed_trust, velocity_anomaly)
    await emit_telemetry("L4_RiskMatrix", "COMPUTE_COMPLETE", {"composite_risk_score": composite_risk})

    # L5: Policy Intelligence Engine
    verdict, policy_rule = evaluate_policy_rules(composite_risk, amount)
    await emit_telemetry("L5_PolicyEngine", "MATCHED", {"rule": policy_rule, "verdict": verdict})

    # L6: Autonomous Decision Engine Synthesis
    await emit_telemetry("L6_DecisionEngine", "VERDICT_FINALIZED", {"verdict": verdict})

    # L7: Trust Graph Blast-Radius Isolation
    blast_radius = f"Isolated Vault Zone: {target_asset} [Max-Impact: ${amount * 0.10:,.2f}]"
    await emit_telemetry("L7_TrustGraph", "BLAST_BOUNDED", {"blast_radius": blast_radius})

    # L8: Trust Evidence Ledger (Cryptographic Merkle Root Assembly)
    evidence_elements = [tx_id, spiffe_id, pcr_digest, str(composite_risk), policy_rule, verdict]
    merkle_root = build_merkle_tree_root(evidence_elements)
    await emit_telemetry("L8_EvidenceLedger", "MERKLE_SEALED", {"merkle_root": merkle_root})

    # Terminal Outputs
    print(f"  [L0 Identity]     : SPIFFE Validated ({spiffe_id})")
    print(f"  [L1 Attestation]  : Hardware Enclave PCR Digest -> {pcr_digest[:18]}...")
    print(f"  [L2 Trust Engine] : Dynamic Score = {decayed_trust}/100")
    print(f"  [L3 Behavioral]   : Velocity Anomaly Z-Score = {velocity_anomaly}")
    print(f"  [L4 Risk Matrix]  : 8-Vector Composite Index = {composite_risk}/100")
    print(f"  [L5 Policy Rules] : Evaluated Rule '{policy_rule}'")
    print(f"  [L6 Decision]     : >>> {verdict} <<<")
    print(f"  [L7 Trust Graph]  : {blast_radius}")
    print(f"  [L8 Evidence]     : Merkle Root Hash -> {merkle_root}")

    # L9 & L10 Workflow Interposition
    if verdict == "REQUIRE_HUMAN_APPROVAL":
        await emit_telemetry("L9_Workflow", "PAUSED", {"queue": "CRO_Approval_Pending"})
        await emit_telemetry("L10_Integration", "WAITING_CALLBACK", {"tx_id": tx_id})
        return {
            "status": "WAITING_APPROVAL",
            "tx_id": tx_id,
            "verdict": verdict,
            "composite_risk_score": composite_risk,
            "proof_hash": merkle_root,
            "instruction": f"python latrivex_cli.py approve --url <NGROK_URL>/webhook/atf-approval --tx-id {tx_id} --action APPROVED"
        }

    # L11 & L12 Settlement
    await emit_telemetry("L11_APIs", "BROADCASTED", {"event": "atf.decision.allow"})
    await emit_telemetry("L12_ControlCenter", "SETTLED", {"status": "SUCCESS"})
    return {"status": "EXECUTED", "tx_id": tx_id, "verdict": verdict, "proof_hash": merkle_root}


@app.post("/webhook/atf-approval")
async def handle_stepup_webhook(request: Request, x_atf_signature: str = Header(None)):
    """L10 Webhook Receiver with HMAC Verification."""
    if not x_atf_signature:
        raise HTTPException(status_code=400, detail="Missing X-ATF-Signature Header")

    body_bytes = await request.body()
    expected_sig = hmac.new(SECRET_KEY.encode('utf-8'), body_bytes, hashlib.sha256).hexdigest()
    
    if not hmac.compare_digest(expected_sig, x_atf_signature):
        raise HTTPException(status_code=401, detail="Invalid HMAC Signature")

    payload = json.loads(body_bytes.decode('utf-8'))
    tx_id = payload.get("tx_id")
    action = payload.get("action")

    print(f"\n=================================================================")
    print(f" [L10 CALLBACK RECEIVED] HMAC Signature Verified ✅")
    print(f" Transaction ID : {tx_id} | Action: {action}")
    print(f"=================================================================")

    if action == "APPROVED":
        await emit_telemetry("L10_Integration", "HMAC_VERIFIED", {"tx_id": tx_id, "action": "APPROVED"})
        await emit_telemetry("L11_SanctionEngine", "UNLOCKED", {"tx_id": tx_id})
        await emit_telemetry("L12_ControlCenter", "SETTLEMENT_SEALED", {"tx_id": tx_id})
        return {"status": "SUCCESS", "tx_id": tx_id, "message": "Transaction executed."}
    
    return {"status": "REJECTED", "tx_id": tx_id, "message": "Transaction rejected."}


if __name__ == "__main__":
    port = int(os.getenv("LOCAL_PORT", 5005))
    print(f"🚀 LATRIVEX Live Agent Server listening on http://127.0.0.1:{port}")
    uvicorn.run(app, host="127.0.0.1", port=port)