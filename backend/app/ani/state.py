"""Conversation state management helpers for Ani."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

_STATE_PATH = Path(__file__).resolve().parent.parent / "state.json"


def _clip_affection(value: int) -> int:
    """Clamp affection to the supported range."""
    return max(0, min(10, value))


@dataclass
class ConversationState:
    """Lightweight state container persisted to disk between chat turns."""

    affection: int = 5
    topic: str = "general"
    turns: int = 0
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path = _STATE_PATH) -> "ConversationState":
        """Load state from disk; fall back to defaults on any error."""
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            affection = _clip_affection(int(data.get("affection", 5)))
            topic = str(data.get("topic", "general")) or "general"
            turns = int(data.get("turns", 0))
            extra = data.get("extra") or {}
            if not isinstance(extra, dict):
                extra = {}
            return cls(
                affection=affection,
                topic=topic,
                turns=max(0, turns),
                extra=extra,
            )
        except FileNotFoundError:
            logger.info("State file not found; using defaults.")
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            logger.warning("Invalid state file detected; resetting to defaults: %s", exc)
        except OSError as exc:
            logger.error("Could not read state file; continuing with defaults: %s", exc)
        return cls()

    def to_dict(self) -> Dict[str, Any]:
        """Serialise the state into a JSON-friendly dictionary."""
        raw = asdict(self)
        raw["affection"] = _clip_affection(raw.get("affection", 5))
        raw["turns"] = max(0, int(raw.get("turns", 0)))
        return raw

    def save(self, path: Path = _STATE_PATH) -> None:
        """Persist state atomically; swallow I/O errors to avoid crashes."""
        payload = json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
        tmp_path = path.with_suffix(".tmp")
        try:
            tmp_path.write_text(payload, encoding="utf-8")
            tmp_path.replace(path)
        except OSError as exc:
            logger.error("Failed to persist state; continuing without saving: %s", exc)
            try:
                if tmp_path.exists():
                    tmp_path.unlink()
            except OSError:
                logger.debug("Unable to clean up temp state file %s", tmp_path)

    def update_after_turn(self, affection_delta: int | None = None, topic: str | None = None) -> None:
        """Increment turn count and optionally adjust affection/topic."""
        self.turns += 1
        if affection_delta is not None:
            self.affection = _clip_affection(self.affection + affection_delta)
        if topic:
            self.topic = topic
