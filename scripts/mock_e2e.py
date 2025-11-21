#!/usr/bin/env python3
import time
import json
import os
import sys
import requests

BASE=os.environ.get('BASE','http://localhost:8000')

payload={
  "projectId": "mock-proj-id", # backend will accept any id for mock demo or create one before
  "tempo": 80,
  "key": "C minor",
  "style": "Romantic",
  "lyrics": "Ami tomar chokhe haralam\nMon poboner moto",
  "instruments": ["Piano","Acoustic Guitar","Pad"]
}

# Create a real project first
resp = requests.post(f"{BASE}/api/projects", json={
  "name": "E2E Mock",
  "tempo": payload["tempo"],
  "key": payload["key"],
  "style": payload["style"],
  "duration_sec": 60,
  "instruments": payload["instruments"],
  "lyrics": payload["lyrics"]
}, timeout=20)
resp.raise_for_status()
projectId = resp.json()["projectId"]
print("Created project:", projectId)

payload["projectId"]=projectId
r = requests.post(f"{BASE}/api/generate/create", json=payload, timeout=20)
r.raise_for_status()
jobId = r.json()["jobId"]
print("Job:", jobId)

while True:
    s = requests.get(f"{BASE}/api/job/{jobId}/status", timeout=20).json()
    print(f"{s['progress']}% - {s['message']}")
    if s.get('logs'): print("  logs:", s['logs'][-1])
    if s['status'] in ('done','error'):
        print("Final:", json.dumps(s.get('result', {}), indent=2))
        if s['status']!='done': sys.exit(2)
        break
    time.sleep(0.8)

print("OK")
