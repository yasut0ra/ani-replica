"""LinUCB contextual bandit implementation."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence

import numpy as np


class LinUCBError(Exception):
    """Base error for LinUCB operations."""


class ArmNotFoundError(LinUCBError):
    """Raised when the requested arm does not exist."""


@dataclass
class ArmState:
    """Holds per-arm matrices for LinUCB."""

    A: np.ndarray
    b: np.ndarray

    def update(self, context: np.ndarray, reward: float) -> None:
        """Update the arm state with a new reward and context."""
        self.A += context @ context.T
        self.b += reward * context

    def theta(self) -> np.ndarray:
        """Return the current weight vector for the arm."""
        return np.linalg.solve(self.A, self.b)

    def confidence_bonus(self, context: np.ndarray, alpha: float) -> float:
        """Return the exploration bonus for the given context."""
        A_inv = np.linalg.inv(self.A)
        variance = float((context.T @ A_inv @ context).item())
        variance = max(variance, 0.0)
        return alpha * math.sqrt(variance)


class LinUCB:
    """Implementation of the LinUCB contextual bandit algorithm."""

    def __init__(self, arms: Iterable[str], context_dim: int, alpha: float = 0.25) -> None:
        arm_list = list(dict.fromkeys(arms))
        if not arm_list:
            raise ValueError("arms must contain at least one unique identifier.")
        if context_dim <= 0:
            raise ValueError("context_dim must be a positive integer.")
        if alpha < 0.0:
            raise ValueError("alpha must be non-negative.")

        self.alpha = float(alpha)
        self.context_dim = int(context_dim)
        identity = np.eye(self.context_dim)
        zero_vec = np.zeros((self.context_dim, 1))

        self._arms: List[str] = arm_list
        self._arm_state: Dict[str, ArmState] = {
            arm: ArmState(A=identity.copy(), b=zero_vec.copy()) for arm in arm_list
        }

    @property
    def arms(self) -> List[str]:
        """Return the registered arms."""
        return list(self._arms)

    def _as_column(self, context: Sequence[float]) -> np.ndarray:
        if len(context) != self.context_dim:
            raise ValueError(
                f"context dimension mismatch: expected {self.context_dim}, got {len(context)}"
            )
        return np.asarray(context, dtype=float).reshape(-1, 1)

    def select_arm(self, context: Sequence[float]) -> str:
        """Select the arm with the highest upper confidence bound."""
        context_vec = self._as_column(context)
        best_arm = None
        best_score = float("-inf")

        for arm in self._arms:
            state = self._arm_state[arm]
            theta = state.theta()
            exploitation = float((theta.T @ context_vec).item())
            exploration = state.confidence_bonus(context_vec, self.alpha)
            score = exploitation + exploration
            if score > best_score:
                best_arm = arm
                best_score = score
        assert best_arm is not None  # guaranteed because arms not empty
        return best_arm

    def update(self, arm: str, reward: float, context: Sequence[float]) -> None:
        """Update the LinUCB statistics for the chosen arm."""
        if arm not in self._arm_state:
            raise ArmNotFoundError(f"Unknown arm: {arm}")
        context_vec = self._as_column(context)
        self._arm_state[arm].update(context_vec, float(reward))

    def arm_state(self, arm: str) -> ArmState:
        """Return the ArmState for inspection/testing."""
        if arm not in self._arm_state:
            raise ArmNotFoundError(f"Unknown arm: {arm}")
        return self._arm_state[arm]
