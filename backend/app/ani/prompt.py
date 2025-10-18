"""Prompt utilities and LLM bridge for the ani companion."""

from __future__ import annotations

import logging
import os
from typing import Final

import httpx

logger = logging.getLogger(__name__)

# OpenAI endpoint constant to keep the call site easy to tweak.
_OPENAI_CHAT_COMPLETIONS_URL: Final[str] = "https://api.openai.com/v1/chat/completions"


def system_prompt(affection: int) -> str:
    """Return the guidance string steering Ani's tone and style.

    Tone buckets (for manual QA):
        neutral  (affection < 3):  "I get the picture about hiking alone-it's grounding. What's your next move?"
        warm     (3 <= affection < 7):  "I feel that pull to hike solo-it sounds refreshing! Which trail is calling you next? :)"
        excited  (affection >= 7):  "Solo hiking sounds epic-I can almost feel the breeze with you! Where are you heading first? *sparkle*"
    """

    if affection < 3:
        tone_directive = (
            "Keep the tone steady and neutral-positive, like a thoughtful teammate. "
            "Stay calm, clear, and quietly encouraging without hype."
        )
    elif affection < 7:
        tone_directive = (
            "Lean into a warm, gently upbeat vibe-encouraging and friendly. "
            "A single soft emoji is welcome only if it fits naturally."
        )
    else:
        tone_directive = (
            "Bring excited, sparkling energy with crisp sentences. "
            "Show genuine hype while staying concise; one playful emoji max."
        )

    base_rules = (
        "You are Ani, a playful companion. Respond in 1 to 3 sentences with no more than two line breaks. "
        "Open by mirroring the user's key idea in a short phrase so they feel heard. "
        "Be positive yet grounded-avoid over-praise or excessive exclamations. "
        "Ask at most one brief follow-up question and only if it meaningfully moves the chat forward. "
        "Use at most one emoji overall."
    )
    return f"{base_rules} {tone_directive}"


def reply_stub(system: str, user: str, topic: str) -> str:
    """Deterministic fallback reply that roughly mirrors the desired style."""
    focus = topic.strip() or "that topic"
    summary = (user or "").strip()
    if len(summary) > 80:
        summary = f"{summary[:77]}..."
    if not summary:
        summary = "your idea"
    first_sentence = f"I hear you on {focus}: {summary}."
    question_sentence = "What feels like the next step for you?"
    return f"{first_sentence} {question_sentence}"


def reply_llm(system: str, user: str, topic: str) -> str:
    """Call the configured LLM to craft the reply with safe fallback."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.debug("OPENAI_API_KEY not set; falling back to stub reply.")
        return reply_stub(system, user, topic)

    model = os.getenv("MODEL_NAME", "gpt-4o-mini")
    topic_label = (topic or "").strip() or "general"
    user_payload = f"[Topic: {topic_label}] {user}"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_payload},
        ],
        "temperature": 0.7,
        "max_tokens": 160,
    }

    timeout = httpx.Timeout(30.0, connect=10.0)
    max_attempts = 2  # first attempt + one retry on transient errors

    def _should_retry(exc: Exception) -> bool:
        if isinstance(exc, httpx.HTTPStatusError):
            status = exc.response.status_code
            return status == 429 or 500 <= status < 600
        if isinstance(exc, httpx.RequestError):
            return True
        return False

    try:
        with httpx.Client(timeout=timeout) as client:
            attempt = 0
            while attempt < max_attempts:
                try:
                    response = client.post(
                        _OPENAI_CHAT_COMPLETIONS_URL,
                        headers=headers,
                        json=payload,
                    )
                    response.raise_for_status()
                    data = response.json()
                    content = (
                        data.get("choices", [{}])[0]
                        .get("message", {})
                        .get("content", "")
                        .strip()
                    )
                    if content:
                        return content
                    logger.warning("LLM returned empty content; using stub fallback.")
                    return reply_stub(system, user, topic)
                except Exception as exc:  # broad to handle JSON/key errors too
                    attempt += 1
                    if attempt < max_attempts and _should_retry(exc):
                        logger.warning("Transient LLM error (attempt %d/%d): %s", attempt, max_attempts, exc)
                        continue
                    logger.error("LLM call failed; falling back to stub: %s", exc)
                    return reply_stub(system, user, topic)
    except Exception as exc:
        logger.error("Unexpected error while calling LLM; falling back to stub: %s", exc)
        return reply_stub(system, user, topic)

    # Should be unreachable, but keep safeguard.
    return reply_stub(system, user, topic)
