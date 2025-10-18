"""FastAPI entry point for the ani companion."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from pydantic import BaseModel, Field

from .ani.prompt import reply_llm, reply_stub, system_prompt
from .ani.state import ConversationState

logger = logging.getLogger(__name__)

app = FastAPI(title="ani-replica")
state = ConversationState.load()


class ChatRequest(BaseModel):
    """Schema for incoming chat requests from the frontend."""

    user: str = Field(..., description="Latest user utterance.")
    topic: str = Field("general", description="Active topic label.")
    affection: int = Field(5, ge=0, le=10, description="Current affection score (0-10).")


class ChatResponse(BaseModel):
    """Response schema sent back to the frontend."""

    reply: str = Field(..., description="Model-crafted response text.")


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Return an LLM-crafted reply with automatic fallback."""
    topic = request.topic or "general"
    affection = request.affection
    state.affection = affection
    state.topic = topic
    system = system_prompt(affection)

    try:
        reply = reply_llm(system=system, user=request.user, topic=topic)
        state.update_after_turn(topic=topic)
        state.save()
        return ChatResponse(reply=reply)
    except Exception as exc:  # pragma: no cover - safeguard for unexpected errors
        logger.exception("Chat handler encountered an error; returning fallback reply: %s", exc)
        fallback = reply_stub(system, request.user, topic)
        try:
            state.update_after_turn(topic=topic)
            state.save()
        except Exception:
            logger.debug("State save failed during fallback handling.")
        return ChatResponse(reply=fallback)
