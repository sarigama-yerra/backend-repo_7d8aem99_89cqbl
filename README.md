# AI Song Generator — Reference Scaffold (Mock-Mode Ready)

This upgrade provides a full dark Suno-style studio, tempo-aware pipeline, mock-mode endpoints, FFmpeg-enabled backend Docker image, and a one-click create flow. It keeps existing logic and adds a safe scaffold to extend with real AI later.

Highlights
- Dark, modern studio UI with violet/cyan accents
- Tempo (BPM) visible and editable everywhere; flows through API payloads and prompts
- Lyrics box above voice options, consent checkbox for voice use
- Voice selector supports WAV/MP3/AMR upload; server validates and returns quality report
- Multi-instrument panel with per-track controls, timeline with lyric markers and tempo grid
- Full pipeline orchestration in mock-mode: Instrumental → Melody → Vocal → Mix → Video
- Download master and video; stems placeholder
- Orchestrator stub + prompts file with explicit tempo references
- Dockerfile includes FFmpeg; docker-compose for local dev (MOCK_MODE=true)

Quick start (mock-mode)
1) Backend (Docker, recommended):
   - cd backend
   - docker compose up --build
   - Backend will be on http://localhost:8000 (OpenAPI at /docs)
2) Frontend (dev server):
   - cd frontend
   - npm install
   - VITE_BACKEND_URL=http://localhost:8000 npm run dev
   - App on http://localhost:3000

Environment vars
- MOCK_MODE=true (default in docker-compose)
- DATABASE_URL, DATABASE_NAME (MongoDB)
- BLUEFLAME_API_KEY (placeholder; not required in mock-mode)

Switching to production
- Implement real calls in blueflame_orchestrator.py and set MOCK_MODE=false + BLUEFLAME_API_KEY
- Replace mock worker steps in main.py with orchestrator methods and handle real assets

Tests
- Run the simple e2e mock script:
  - cd backend
  - python3 scripts/mock_e2e.py

Postman / OpenAPI
- OpenAPI available at /docs when backend runs. A Postman collection can be exported from the OpenAPI.

Acceptance checklist
- Backend runs and exposes /test as OK
- POST /api/upload/voice accepts .amr and returns voiceProfileId + qualityReport
- POST /api/generate/create returns jobId and /api/job/:jobId/status reaches done with masterUrl & videoUrl in mock-mode

Notes
- This scaffold avoids touching secrets and preserves existing custom logic. If you flip MOCK_MODE to false without an API key, the frontend shows a banner advising to set the key.
