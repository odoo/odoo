from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass(slots=True)
class LoadingPhase:
    reinit_modules: set[str] = field(default_factory=set)
    xmlids_written: set[str] = field(default_factory=set)
    xmlid_recorder: set[str] | None = None
    ref_recorder: dict[str, int] | None = None
    load_language_done: bool = False
    addon_state: dict[str, Any] = field(default_factory=dict)

    def state[T](self, key: str, factory: Callable[[], T]) -> T:
        try:
            return self.addon_state[key]
        except KeyError:
            value = self.addon_state[key] = factory()
            return value
