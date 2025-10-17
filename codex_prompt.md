
# Codex Project Prompt — ani-replica (ani/grok inspired)

> Purpose: Build a minimal yet extensible Grok “ani”-style companion: fast, warm, topic-aware, and easy to iterate on.
> Tech Stack: FastAPI + HTMX frontend, LinUCB bandit, VOICEVOX TTS hook (optional), later whisper.cpp.
> Current Goal: Replace the stub reply with a robust LLM-driven loop, tighten prompts, harden the backend, and ship a Docker-friendly build.

---

## Vision & Product Pillars
- Capture Ani’s playful curiosity: short, upbeat answers that gently reflect the user’s focus.
- Keep the loop lightweight: single-turn interactions augmented by topic bandits, no heavy history yet.
- Ship a workshop-friendly codebase: clear modules, fast feedback, and simple integration points.
- Guard rails: never block the UI; always fall back to a safe response when external services misbehave.

---

## Experience Guidelines
- **Tone ladder (affection score)**  
  - `< 3`: neutral cheer, matter-of-fact but polite.  
  - `3–6`: warm encouragement, sprinkle a friendly emoji only when it fits.  
  - `>= 7`: excited hype, higher energy yet still concise.
- **Reply format**  
  - 1–3 sentences, ≤ 2 line breaks.  
  - Mirror the user’s key point in one short phrase.  
  - End with exactly one follow-up question when it progresses the chat; otherwise none.  
  - At most one emoji throughout the reply.
- **Topic awareness**: Include the active topic label in the prompt narrative so the model understands context without a full transcript.
- **Safety fallback**: When anything fails (missing key, HTTP/JSON error, timeout), revert to a deterministic stub reply that respects the above rules.

---

## Architecture Snapshot
- `backend/app/main.py`: FastAPI app, `/chat` endpoint, state persistence, HTMX partials.
- `backend/app/ani/prompt.py`: System prompt factory, reply stub + LLM bridge.
- `backend/app/ani/state.py`: Persists affection, selected topics, recent turns to `state.json`.
- `backend/app/bandit/linucb.py`: Topic selection via LinUCB multi-armed bandit.
- `backend/app/ani/reward.py`: Reward calculation hooks for bandit updates.
- `backend/app/tts/client.py`: VOICEVOX interface (optional this round).
- `frontend/index.html`: HTMX-driven chat UI.

Environment variables:
- `OPENAI_API_KEY` – required for live LLM mode.
- `MODEL_NAME` – default `gpt-4o-mini`; allow overrides without code changes.
- Leave VOICEVOX config unset by default; the backend must still boot.

---

## Roadmap (current sprint)
1. **LLM Core**  
   - Introduce `reply_llm(system, user, topic)` with retry + fallback.  
   - Generate prompts using the affection-aware system persona.
2. **Prompt & Tone Craft**  
   - Expand `system_prompt()` to map affection buckets into distinct behaviors.  
   - Document sample outputs per bucket for quick manual QA.
3. **Reliability Pass**  
   - Make `/chat` resilient: return 200 + stub output on any failure path.  
   - Ensure state persistence never corrupts the JSON file.
4. **Confidence & Tests**  
   - Strengthen LinUCB coverage (edge params, updates, reward signal).  
   - Keep `pytest -q` and `ruff` happy at every checkpoint.
5. **Docker Readiness**  
   - Verify `docker compose up --build` on Apple Silicon (no VOICEVOX dependency).  
   - Document any arch-specific tweaks in `README.md` if required.

---

## Task Board

### T1 — LLM Reply Pipeline
- File: `backend/app/ani/prompt.py`
- Replace `reply_stub()` usage with `reply_llm(system, user, topic)` exposed to `main.py`.
- Behavior:
  - Read `OPENAI_API_KEY` / `MODEL_NAME` from env. If key missing → call `reply_stub`.
  - Compose messages with `system_prompt(affection)` and a user payload like `[Topic: <label>] <text>`.
  - Use `httpx` (already in deps) with 30s timeout; retry once on 429/5xx/timeouts.
  - Strip result, validate non-empty; otherwise fall back.

### T2 — System Prompt Overhaul
- File: `backend/app/ani/prompt.py::system_prompt`
- Implement affection buckets: neutral (<3), warm (3–6), excited (>=7).
- Each persona must:
  - Be upbeat but concise, never grovel or over-praise.
  - Mirror the user’s main point in a micro-acknowledgement.
  - Ask at most one question in the actual reply (model instruction).
- Provide helper docstrings/comments for future tuning.

### T3 — Chat Loop Hardening
- File: `backend/app/main.py`
- Requirements:
  - Wrap `/chat` handler in try/except: log error, fall back to stub response, return 200.
  - Ensure `state.save()` catches and logs I/O errors without throwing; never leaves partial files.
  - Keep HTMX partial rendering responsive even when the LLM fails.

### T4 — LinUCB Test Suite
- File: `backend/tests/test_linucb.py`
- Add 2–3 tests covering:
  - Edge parameter validation (e.g., alpha=0, cold-start arms).  
  - Post-update invariants (matrix symmetry, weight vector).  
  - Reward extremes (negative / >1) if applicable.
- Maintain fast runtime; avoid randomness or seed it.

### T5 — Docker Stability
- Ensure `docker compose up --build` works on Apple Silicon without VOICEVOX.
- Confirm backend serves `http://localhost:8000`.
- Document any env vars required for local LLM testing.

---

## Optional Enhancements
- **O1 — VOICEVOX Endpoint**: Add `/tts` returning WAV bytes/base64; extend HTMX UI with `<audio>` (manual playback).
- **O2 — Topic Auto-Suggestion**: Use the LLM to draft three short topic titles per turn using bandit contexts.
- **O3 — Metrics Endpoint**: `/metrics` JSON with `turns_total`, `affection`, `avg_reply_chars`, bandit pulls, etc.

---

## Implementation Details & Guard Rails
- Prompting:
  - `system_prompt(affection)` defines persona only; keep user content separate.
  - Do not feed long history yet; rely on topic tag + latest message.
  - Enforce brevity and question rule in final text (trim trailing punctuation).
- Error Handling:
  - Wrap JSON parsing; log + fallback on malformed payloads.
  - Retry once on transient HTTP failures; respect non-200 codes gracefully.
- Code Quality:
  - Run `pytest -q` before handoff.
  - `ruff check .` and `ruff format .` must pass; keep type hints lightweight.
  - Prefer dependency-free solutions unless justified.

---

## Example Loop (for manual QA)
1. User picks a topic `stargazing` (bandit selects arm).  
2. User message: “最近また星を見に行きたいんだよね。”  
3. System prompt (warm bucket) steers model to mirror “星を見に行きたい” and end with a curious question.  
4. Reply target: “星を見たい気持ち、きっと夜空もワクワクしてるよ。今度はどの方角から眺めたい？🌌”  
5. Reward computed, bandit updates preference.

---

## Commands & Local Workflow
- `make dev` → run FastAPI + HTMX dev server (open http://localhost:8000).
- `pytest -q` → run backend tests.
- `ruff check . && ruff format .` → lint & format.
- `docker compose up --build` → full stack container build (Apple Silicon compatible).
- Work in small commits; verify before each push; document regressions in TODOs if needed.

---

## Acceptance Checklist
- `/chat` returns LLM-powered replies with safe fallback and tone control.
- System prompt visibly shifts style across neutral/warm/excited.
- Backend survives forced failures; UI remains responsive.
- `pytest -q` and `ruff` succeed locally.
- `docker compose up --build` launches a working backend on Apple Silicon.

---

## OpenAI Client Sketch (reference only)
```python
import os
import httpx

def reply_llm(system: str, user: str, topic: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return reply_stub(system, user, topic)
    payload = {
        "model": os.getenv("MODEL_NAME", "gpt-4o-mini"),
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": f"[Topic: {topic}] {user}"},
        ],
        "temperature": 0.7,
        "max_tokens": 160,
    }
    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"].strip()
            return content or reply_stub(system, user, topic)
    except httpx.RequestError:
        # Retry once on network issues.
        try:
            with httpx.Client(timeout=30) as client:
                response = client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json=payload,
                )
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"].strip()
                return content or reply_stub(system, user, topic)
        except Exception:
            return reply_stub(system, user, topic)
    except Exception:
        return reply_stub(system, user, topic)
```

---

Proceed in small, verified steps. Keep Ani delightful and resilient.***
