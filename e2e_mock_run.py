import json
import time
import requests

BASE = "http://localhost:8000"

def main():
    # Minimal e2e mock run
    print("Creating project...")
    r = requests.post(f"{BASE}/api/projects", json={
        "name": "E2E Test",
        "tempo": 90,
        "key": "A minor",
        "style": "Romantic",
        "duration_sec": 60,
        "instruments": ["Piano", "Strings"],
        "lyrics": "Ami tomay bhalobashi\nKeno je mon amar hasi"
    })
    r.raise_for_status()
    pid = r.json()["projectId"]
    print("Project:", pid)

    print("Start full pipeline (mock)...")
    r = requests.post(f"{BASE}/api/generate/create", json={
        "projectId": pid,
        "tempo": 90,
        "key": "A minor",
        "style": "Romantic",
        "lyrics": "Ami tomay bhalobashi\nKeno je mon amar hasi",
        "instruments": ["Piano", "Strings"]
    })
    r.raise_for_status()
    job = r.json()["jobId"]
    print("Job:", job)

    while True:
        s = requests.get(f"{BASE}/api/job/{job}/status").json()
        print(f"status={s['status']} progress={s['progress']} message={s['message']}")
        if s["status"] in ("done", "error"):
            print(json.dumps(s.get("result", {}), indent=2))
            break
        time.sleep(0.7)

if __name__ == "__main__":
    main()
