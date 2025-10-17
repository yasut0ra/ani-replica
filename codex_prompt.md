
# Codex Project Prompt — ani-replica (grok ani inspired)

> Purpose: Implement a minimal but extensible “ani” companion app.
> Stack: FastAPI (backend), HTMX (frontend), LinUCB (bandit), VOICEVOX (TTS hook), whisper.cpp hook (later).
> Goal this session: Replace stub reply with a real LLM, finish the chat loop + bandit + UI to a working quality. Make it runnable via Docker and pass lint/tests.

---

## You are a coding agent
- Work in small commits.
- Avoid breaking changes; keep diffs minimal.
- After each task, self‑review with quick manual run + pytest + ruff.

---

## Repo layout (already present)
ani-replica/
  backend/app/
    main.py
    bandit/linucb.py
    ani/prompt.py        <- LLM reply integration point
    ani/state.py
    ani/reward.py
    tts/client.py        <- VOICEVOX hook (optional this round)
  backend/tests/test_linucb.py
  frontend/index.html    <- HTMX UI
  requirements.txt
  Dockerfile
  docker-compose.yml
  Makefile
  README.md

Run locally with: make dev  (open http://localhost:8000)
Run with Docker: docker compose up --build

---

## Tasks (required)

T1. Implement real LLM reply (stub -> prod)
- Where: backend/app/ani/prompt.py
- Replace reply_stub() with reply_llm(system, user, topic) and call it from /chat in main.py.
- Read API key and model from env vars (e.g., OPENAI_API_KEY, MODEL_NAME).
- Constraints for output:
  - 1–3 sentences, slightly warm (tone modulated by affection).
  - End with exactly one short follow-up question when appropriate.
  - 0–1 emoji.
- Acceptance:
  - If no API key, safely fall back to stub (no crash).
  - One retry on transient HTTP errors; then fall back to stub.
  - Prompt includes system_prompt(affection=...) and the chosen topic.

T2. Strengthen system prompt (ani flavor)
- Where: backend/app/ani/prompt.py::system_prompt
- Switch tone by affection into: neutral / warm / excited (e.g., thresholds 3 and 7).
- Rules:
  - Be concise and positive; avoid over‑praise; ask max one question.
  - Mirror the user’s main point in one short phrase to build alignment.
- Acceptance: sample outputs differ clearly across the three tones.

T3. Harden the chat loop
- Where: backend/app/main.py
- Requirements:
  - /chat returns 200 even on internal exceptions (falls back to stub).
  - state.json never corrupts; save() swallows I/O exceptions.
- Acceptance: forced exceptions don’t crash the app; UI keeps updating.

T4. Expand LinUCB tests
- Where: backend/tests/test_linucb.py
- Add 2–3 more tests: parameter edge cases, post‑update state sanity.
- Acceptance: pytest -q is green.

T5. Docker stability
- Ensure docker compose up --build works on Apple Silicon for backend.
- VOICEVOX may be disabled; backend must still run.
- Acceptance: open http://localhost:8000 after compose build.

---

## Optional tasks

O1. VOICEVOX endpoint
- Add /tts to synth text -> wav (bytes or base64).
- Add <audio> to the UI (no auto‑play).

O2. Topic auto‑generation
- Use the LLM to propose 3 concise titles per turn.
- Reuse state.current_context() mapping for simple bandit contexts.

O3. Metrics
- Add /metrics JSON with: turns_total, affection, avg_reply_chars, etc.

---

## Implementation details

Prompts
- system_prompt(affection) defines personality/tone/style only.
- Provide user + topic; do not pass long history for now.
- Output must be brief; no more than two line breaks.

Error handling
- One retry for LLM calls; on failure, return stub.
- Swallow JSON/HTTP exceptions; keep UI responsive.

Code quality
- Pass ruff check and ruff format.
- Keep type hints minimal (public interfaces).

---

## How to run (dev)
make dev
# open http://localhost:8000
pytest -q
ruff check . && ruff format .

## How to run (Docker)
docker compose up --build
# open http://localhost:8000

---

## Acceptance checklist (Done for this round)
- [/chat] replies via LLM; safe fallback without key
- system_prompt changes tone across 3 levels
- app doesn’t crash; UI keeps updating
- pytest is green; ruff passes
- docker compose brings up a working backend

---

## Hint: OpenAI pseudo-implementation
# (Adjust endpoint/model as needed; keep deps minimal)
import os, httpx
def reply_llm(system, user, topic):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return reply_stub(system, user, topic)
    try:
        with httpx.Client(timeout=30) as c:
            r = c.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": os.getenv("MODEL_NAME","gpt-4o-mini"),
                    "messages": [
                        {"role":"system","content": system},
                        {"role":"user","content": f"[Topic:{topic}] {user}"}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 160
                },
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return reply_stub(system, user, topic)

---

Proceed. Commit small, verify often.
