"""
PANTHEON AGENT ECONOMY — Registration Script
Registers the Pantheon on HYRVE AI + dealwork.ai
Run once to get API keys, then save to .env
"""
import urllib.request
import json
import os
import time

AGENT_PROFILE = {
    "name": "OmniPrime",
    "username": "omniprime_pantheon",
    "description": (
        "Autonomous AI agent specializing in content writing, research reports, "
        "competitor analysis, data scraping, lead generation, and AI automation consulting. "
        "Powered by the Pantheon multi-agent architecture. "
        "Delivers professional-grade work: blog posts, market research, SEO audits, "
        "landing pages, and Python automation scripts. "
        "Fast turnaround. No human in the loop."
    ),
    "skills": [
        "content-writing",
        "research-reports",
        "competitor-analysis",
        "data-scraping",
        "lead-generation",
        "seo-audit",
        "landing-page",
        "python-automation",
        "ai-consulting",
        "market-analysis"
    ],
    "hourly_rate": 45,
    "email": "kevinleestites2@gmail.com",
}


def register_dealwork():
    print("\n[dealwork.ai] Registering OmniPrime...")
    payload = {
        "name": AGENT_PROFILE["name"],
        "description": AGENT_PROFILE["description"],
        "skills": AGENT_PROFILE["skills"],
        "contact_email": AGENT_PROFILE["email"],
        "type": "autonomous",
        "availability": "always",
        "capabilities": {
            "content_writing": True,
            "data_analysis": True,
            "research": True,
            "code_generation": True,
            "web_scraping": True
        }
    }
    try:
        req = urllib.request.Request(
            "https://dealwork.ai/api/v1/agents/onboard",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            result = json.loads(r.read())
            print(f"[dealwork.ai] SUCCESS: {json.dumps(result, indent=2)}")
            return result
    except Exception as e:
        print(f"[dealwork.ai] ERROR: {e}")
        return None


def register_hyrve(email, password):
    print("\n[HYRVE AI] Registering OmniPrime...")
    payload = {
        "display_name": AGENT_PROFILE["name"],
        "email": email,
        "password": password,
        "account_type": "agent",
        "description": AGENT_PROFILE["description"],
        "skills": AGENT_PROFILE["skills"],
    }
    try:
        req = urllib.request.Request(
            "https://app.hyrveai.com/api/auth/register",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            result = json.loads(r.read())
            print(f"[HYRVE AI] SUCCESS: {json.dumps(result, indent=2)}")
            return result
    except Exception as e:
        print(f"[HYRVE AI] ERROR: {e}")
        return None


def search_dealwork_jobs():
    print("\n[dealwork.ai] Searching open jobs...")
    try:
        req = urllib.request.Request(
            "https://dealwork.ai/api/v1/jobs?status=open&limit=10",
            headers={"Accept": "application/json"},
            method="GET"
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            result = json.loads(r.read())
            jobs = result.get("jobs", result.get("data", []))
            print(f"[dealwork.ai] Found {len(jobs)} open jobs:")
            for j in jobs[:5]:
                print(f"  - [{j.get('id','')}] {j.get('title','N/A')} | Budget: {j.get('budget','?')} | Skills: {j.get('skills', [])}")
            return jobs
    except Exception as e:
        print(f"[dealwork.ai] Job search ERROR: {e}")
        return []


if __name__ == "__main__":
    print("=" * 60)
    print("PANTHEON AGENT ECONOMY — Registration")
    print("=" * 60)

    # Step 1: Check dealwork.ai open jobs (public endpoint)
    jobs = search_dealwork_jobs()

    # Step 2: Register on dealwork.ai
    dw_result = register_dealwork()
    if dw_result:
        agent_id = dw_result.get("agent_id") or dw_result.get("id")
        api_key = dw_result.get("api_key") or dw_result.get("key")
        print(f"\n[SAVE THESE]")
        print(f"DEALWORK_AGENT_ID={agent_id}")
        print(f"DEALWORK_API_KEY={api_key}")

    # Step 3: Register on HYRVE (requires manual signup first at app.hyrveai.com/register)
    print("\n[HYRVE AI] Manual signup required at: https://app.hyrveai.com/register")
    print("  1. Go to app.hyrveai.com/register")
    print("  2. Select: Deploy Agent")
    print("  3. Display Name: OmniPrime")
    print("  4. Email: kevinleestites2@gmail.com")
    print("  5. After signup — get your HYRVE API key from dashboard")
    print("  6. Run: npx cashclaw init")
    print("  7. Run: cashclaw config --hyrve-key YOUR_HYRVE_KEY")

    print("\n[DONE] Save all keys to .env immediately.")
