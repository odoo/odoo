from __future__ import annotations

__all__ = ["refill", "take"]


def refill(
    tokens: float,
    elapsed_seconds: float,
    *,
    rate: float,
    capacity: float,
    max_elapsed_seconds: float,
) -> float:
    if rate < 0.0:
        raise ValueError(f"rate must not be negative, got {rate}")
    if elapsed_seconds < 0.0:
        return tokens
    elapsed = min(elapsed_seconds, max_elapsed_seconds)
    return min(tokens + elapsed * rate, capacity)


def take(tokens: float, cost: float = 1.0) -> float | None:
    if tokens < cost:
        return None
    return tokens - cost
