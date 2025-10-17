"""FastAPI entry point for the ani companion."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from pydantic import BaseModel, Field

from .ani.prompt import reply_llm, system_prompt

logger = logging.getLogger(__name__)

app = FastAPI(title="ani-replica")


class ChatRequest(BaseModel):
    """Schema for incoming chat requests from the frontend."""

    user: str = Field(..., description="Latest user utterance.")
    topic: str = Field("general", description="Active topic label.")
    affection: int = Field(5, description="Current affection score (0-10).")


class ChatResponse(BaseModel):
    """Response schema sent back to the frontend."""

    reply: str = Field(..., description="Model-crafted response text.")


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Return an LLM-crafted reply with automatic fallback."""
    system = system_prompt(request.affection)
    reply = reply_llm(system=system, user=request.user, topic=request.topic)
    return ChatResponse(reply=reply)

