from collections.abc import Callable
from typing import Any


def registry_singleton(env: Any, attribute: str, factory: Callable[[], Any]) -> Any:
    """Build (or fetch) one instance per worker process, not per request.

    ``env.registry`` is a plain in-process object: under ``--workers=N``
    each prefork worker is a separate OS process with its own heap, so this
    singleton is process-local, not cluster-wide. A caller sharing state
    across all workers needs a DB- or Redis-backed store instead.
    """
    registry = env.registry
    instance = getattr(registry, attribute, None)
    if instance is None:
        instance = factory()
        setattr(registry, attribute, instance)
    return instance
