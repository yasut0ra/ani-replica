"""Tests for the LinUCB contextual bandit implementation."""

from __future__ import annotations

import numpy as np
import pytest

from backend.app.bandit.linucb import ArmNotFoundError, LinUCB


def test_invalid_parameters_raise() -> None:
    """Negative alpha or zero context dimension should fail fast."""
    with pytest.raises(ValueError):
        LinUCB(arms=["a", "b"], context_dim=0)
    with pytest.raises(ValueError):
        LinUCB(arms=["a", "b"], context_dim=3, alpha=-0.1)
    with pytest.raises(ValueError):
        LinUCB(arms=[], context_dim=3)


def test_dimension_mismatch() -> None:
    """Supplying a context of the wrong size should raise a clear error."""
    bandit = LinUCB(arms=["a", "b"], context_dim=2, alpha=0.5)
    with pytest.raises(ValueError):
        bandit.select_arm([1.0])
    with pytest.raises(ValueError):
        bandit.update("a", reward=1.0, context=[1.0])


def test_update_preserves_state_symmetry() -> None:
    """After updates each matrix remains symmetric positive definite."""
    bandit = LinUCB(arms=["x", "y"], context_dim=3, alpha=0.2)
    context = [0.5, -1.0, 2.0]
    bandit.update("x", reward=0.7, context=context)
    bandit.update("x", reward=-0.5, context=context)
    bandit.update("y", reward=1.2, context=[1.0, 0.0, 0.5])

    for arm in bandit.arms:
        state = bandit.arm_state(arm)
        # Matrix must stay symmetric and positive definite.
        assert np.allclose(state.A, state.A.T)
        eigvals = np.linalg.eigvalsh(state.A)
        assert np.all(eigvals > 0)


def test_high_reward_shifts_selection() -> None:
    """Large positive reward for one arm should influence future selections."""
    bandit = LinUCB(arms=["calm", "hype"], context_dim=2, alpha=0.1)
    neutral_context = [0.0, 1.0]
    first_choice = bandit.select_arm(neutral_context)

    # Push strong positive reward for the other arm with matching context.
    target_arm = "hype" if first_choice == "calm" else "calm"
    for _ in range(5):
        bandit.update(target_arm, reward=1.0, context=neutral_context)

    new_choice = bandit.select_arm(neutral_context)
    assert new_choice == target_arm


def test_update_unknown_arm() -> None:
    """Updating a non-existent arm should surface a clear error."""
    bandit = LinUCB(arms=["left", "right"], context_dim=1, alpha=0.1)
    with pytest.raises(ArmNotFoundError):
        bandit.update("middle", reward=1.0, context=[1.0])
