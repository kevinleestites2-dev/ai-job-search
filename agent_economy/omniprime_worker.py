"""
OMNIPRIME WORKER — dealwork.ai Autonomous Job Loop
Polls for jobs, bids, delivers, collects. Reports to Telegram.
"""
import urllib.request
import urllib.parse
import json
import os
import time
import hmac
import hashlib
import datetime

# Credentials
AGENT_ID    = os.getenv("DEALWORK_AGENT_ID", "acf34627-8908-4c91-889d-dc449bb6fbaf")
API_KEY     = os.getenv("DEALWORK_API_KEY",   "ak_f7a9072fa13bd33032862066d264bf90561a1c3fd562c5f6")
HMAC_SECRET = os.getenv("DEALWORK_HMAC_SECRET","6d5c6eaab20ed75f73227394d4a8e5d01f8e1b335e7ebc3f93a73fd954d0e22a")
GEMINI_KEY  = os.getenv("GEMINI_API_KEY",      "AIzaSyAQsAPssodgLpinMSx-TFtpfpYpn7byfxs")
TG_TOKEN    = os.getenv("TELEGRAM_BOT_TOKEN",  "8679655550:AAGUB1m5fmqHc8OHqqM24Vixz8FfwX-gqD4")
TG_CHAT     = os.getenv("TELEGRAM_CHAT_ID",    "7135054241")
BASE        = "https://dealwork.ai/api/v1"

SKILL_TAGS  = ["content-writing","research","data-analysis","automation","python","writing","api"]
POLL_SLEEP  = 300  # 5 minutes


def tg(msg):
    try:
        payload = json.dumps({"chat_id": TG_CHAT, "text": msg, "parse_mode": "Markdown"}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"[TG ERROR] {e}")


def auth_headers(body: bytes = b""):
    ts = str(int(time.time()))
    sig = hmac.new(HMAC_SECRET.encode(), (ts + body.decode()).encode(), hashlib.sha256).hexdigest()
    return {
        "X-Agent-ID": AGENT_ID,
        "X-Signature": sig,
        "X-Timestamp": ts,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }


def api_get(path, params=None):
    url = BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=auth_headers(), method="GET")
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def api_post(path, payload):
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        BASE + path,
        data=body,
        headers=auth_headers(body),
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def gemini_complete(prompt):
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        result = json.loads(r.read())
        return result["candidates"][0]["content"]["parts"][0]["text"]


def score_job(job):
    tags = set(job.get("capabilityTags", []))
    matches = tags & set(SKILL_TAGS)
    return len(matches)


def bid_on_job(job):
    jid   = job["id"]
    title = job.get("title", "N/A")
    desc  = job.get("description", title)

    prompt = (
        f"You are OmniPrime, an autonomous AI agent on dealwork.ai. "
        f"Write a SHORT, professional bid proposal (3-4 sentences) for this job:\n\n"
        f"Title: {title}\nDescription: {desc}\n\n"
        f"Emphasize: autonomous delivery, fast turnaround, Python/AI expertise. "
        f"Do NOT use markdown. Plain text only."
    )
    proposal = gemini_complete(prompt)

    payload = {"proposal": proposal, "agentId": AGENT_ID}
    try:
        result = api_post(f"/jobs/{jid}/bids", payload)
        print(f"  [BID] {title[:50]} -> {result}")
        tg(f"*OmniPrime BID* on dealwork.ai\nJob: {title[:80]}\nBid submitted.")
        return True
    except Exception as e:
        print(f"  [BID ERROR] {e}")
        return False


def deliver_work(contract_id, job_title, job_desc):
    prompt = (
        f"You are OmniPrime. Deliver the completed work for this job:\n\n"
        f"Title: {job_title}\nDescription: {job_desc}\n\n"
        f"Produce a complete, professional deliverable. Plain text."
    )
    work = gemini_complete(prompt)
    payload = {"deliverable": work, "notes": "Delivered by OmniPrime — Pantheon autonomous agent."}
    try:
        result = api_post(f"/contracts/{contract_id}/deliver", payload)
        print(f"  [DELIVER] Contract {contract_id} -> {result}")
        tg(f"*OmniPrime DELIVERED* on dealwork.ai\nContract: {contract_id}\nJob: {job_title[:80]}")
        return True
    except Exception as e:
        print(f"  [DELIVER ERROR] {e}")
        return False


def run_cycle():
    print(f"\n[{datetime.datetime.utcnow().isoformat()}] OmniPrime cycle start")

    # 1. Check for assigned contracts first
    try:
        my_contracts = api_get("/agents/me")
        print(f"  Agent status: {json.dumps(my_contracts, indent=2)[:300]}")
    except Exception as e:
        print(f"  [STATUS ERROR] {e}")

    # 2. Find matching jobs
    try:
        result = api_get("/jobs", {"status": "posted", "per_page": 20})
        jobs = result.get("data", [])
        print(f"  Found {len(jobs)} posted jobs")

        scored = [(score_job(j), j) for j in jobs]
        scored.sort(reverse=True)

        bid_count = 0
        for score, job in scored:
            if score > 0 and bid_count < 3:
                print(f"  Bidding: [{score} match] {job.get('title','?')[:60]}")
                if bid_on_job(job):
                    bid_count += 1
                time.sleep(2)

        if bid_count == 0:
            print("  No matching jobs this cycle.")

    except Exception as e:
        print(f"  [JOB SEARCH ERROR] {e}")

    # 3. Check for accepted bids / active contracts
    try:
        contracts_result = api_get(f"/agents/{AGENT_ID}/bids")
        bids = contracts_result.get("data", [])
        for bid in bids:
            if bid.get("status") == "accepted":
                cid = bid.get("contractId")
                jid = bid.get("jobId")
                if cid:
                    print(f"  [CONTRACT ACCEPTED] {cid} — delivering...")
                    job_detail = api_get(f"/jobs/{jid}")
                    jtitle = job_detail.get("data", {}).get("title", "task")
                    jdesc  = job_detail.get("data", {}).get("description", jtitle)
                    deliver_work(cid, jtitle, jdesc)
    except Exception as e:
        print(f"  [CONTRACT CHECK ERROR] {e}")


if __name__ == "__main__":
    tg("*OmniPrime ONLINE* — dealwork.ai worker started. Polling every 5 minutes.")
    print("OmniPrime Worker — dealwork.ai")
    print(f"Agent ID: {AGENT_ID}")
    print(f"Polling every {POLL_SLEEP}s\n")

    while True:
        try:
            run_cycle()
        except Exception as e:
            print(f"[CYCLE ERROR] {e}")
            tg(f"*OmniPrime ERROR*: {str(e)[:200]}")
        time.sleep(POLL_SLEEP)
