from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import replace
from typing import Any, Protocol

__all__ = ["OptionSource", "SettingsSlot"]


class OptionSource(Protocol):
    def __getitem__(self, key: str, /) -> Any: ...


class SettingsSlot[T]:
    __slots__ = ("_installed", "_memo", "_name", "_source", "_version")

    def __init__(
        self,
        name: str,
        source: Callable[[], T] | None = None,
        *,
        version: Callable[[], object] | None = None,
    ) -> None:
        self._name = name
        self._source = source
        self._version = version
        self._memo: tuple[object, T] | None = None
        self._installed: T | None = None

    def provide(self, source: Callable[[], T]) -> None:
        self._source = source

    @property
    def is_installed(self) -> bool:
        return self._installed is not None

    def current(self) -> T:
        if self._installed is not None:
            return self._installed
        if self._source is None:
            raise RuntimeError(
                f"{self._name} has no settings source and nothing installed; "
                f"the process bootstrap provides one before the first read"
            )
        if self._version is None:
            return self._source()
        stamp = self._version()
        memo = self._memo
        if memo is not None and memo[0] == stamp:
            return memo[1]
        settings = self._source()
        self._memo = (stamp, settings)
        return settings

    @contextmanager
    def installed(self, settings: T) -> Iterator[T]:
        previous = self._installed
        self._installed = settings
        try:
            yield settings
        finally:
            self._installed = previous

    @contextmanager
    def override(self, **changes: Any) -> Iterator[T]:
        with self.installed(replace(self.current(), **changes)) as settings:  # type: ignore[type-var]
            yield settings
