from __future__ import annotations

import itertools
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Protocol, Self

import psycopg.errors

from odoo.exceptions import ConcurrencyError
from odoo.libs.debug_log import DebugLog

if TYPE_CHECKING:
    from .cursor import BaseCursor

_savepoint_counter = itertools.count()
_debug = DebugLog(__name__)


class SavepointHost(Protocol):
    def execute(self, query: Any, /, *args: Any, **kwargs: Any) -> Any: ...


class Savepoint:
    __slots__ = ("_cr", "closed", "name")

    _restores_orm_state: bool = False

    def __init__(self, cr: SavepointHost):
        self.name = f"sp{next(_savepoint_counter)}"
        self._cr = cr
        self.closed: bool = False
        cr.execute(f'SAVEPOINT "{self.name}"')
        if hasattr(cr, "_savepoint_depth"):
            cr._savepoint_depth += 1
        _debug.lifecycle(
            "savepoint.opened",
            name=self.name,
            depth=getattr(cr, "_savepoint_depth", None),
            flushing=self._restores_orm_state,
        )

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        self.close(rollback=exc_type is not None)

    def close(self, *, rollback: bool = True) -> None:
        if not self.closed:
            self._close(rollback)

    def rollback(self) -> None:
        if self.closed:
            _debug.logic("savepoint.rollback_refused", name=self.name, reason="closed")
            raise RuntimeError(
                f'Savepoint "{self.name}" is already closed; cannot roll back'
            )
        _debug.lifecycle(
            "savepoint.rolled_back",
            name=self.name,
            depth=getattr(self._cr, "_savepoint_depth", None),
        )
        self._cr.execute(f'ROLLBACK TO SAVEPOINT "{self.name}"')

    def _close(self, rollback: bool) -> None:
        try:
            if rollback:
                self.rollback()
            self._cr.execute(f'RELEASE SAVEPOINT "{self.name}"')
        finally:
            self.closed = True
            if hasattr(self._cr, "_savepoint_depth"):
                self._cr._savepoint_depth -= 1
            _debug.lifecycle("savepoint.closed", name=self.name, rollback=rollback)


class _FlushingSavepoint(Savepoint):
    __slots__ = ()

    if TYPE_CHECKING:
        _cr: BaseCursor

    def __init__(self, cr: BaseCursor) -> None:
        with _debug.perf(
            "savepoint.flush_before_open",
            cr=cr,
            db=getattr(cr, "dbname", None),
            depth=getattr(cr, "_savepoint_depth", None),
        ):
            cr.flush()
        self._save_orm_state(cr)
        super().__init__(cr)

    def _save_orm_state(self, cr: BaseCursor) -> None:
        pass

    def _restore_orm_state(self, cr: BaseCursor) -> None:
        pass

    def rollback(self) -> None:
        cr = self._cr
        super().rollback()
        if cr.transaction is not None:
            with _debug.perf("savepoint.orm_state_restored", cr=cr, name=self.name):
                self._restore_orm_state(cr)

    def _close(self, rollback: bool) -> None:
        cr = self._cr
        try:
            if not rollback:
                with _debug.perf(
                    "savepoint.flush_before_release", cr=cr, name=self.name
                ):
                    cr.flush()
        except Exception as e:
            rollback = True
            _debug.logic(
                "savepoint.flush_failed", name=self.name, error=type(e).__name__
            )
            raise
        finally:
            super()._close(rollback)


def get_or_create_row[T](
    cr: Any,
    insert: Callable[[], T],
    find: Callable[[], T],
    *,
    conflict: str,
    flush: bool = True,
) -> tuple[T, bool]:
    try:
        with cr.savepoint(flush=flush):
            inserted = insert()
            _debug.logic("savepoint.get_or_create.inserted", conflict=conflict)
            return inserted, True
    except psycopg.errors.UniqueViolation:
        existing = find()
        _debug.logic(
            "savepoint.get_or_create.conflict", conflict=conflict, found=bool(existing)
        )
        if not existing:
            raise ConcurrencyError(
                f"{conflict} was created by a concurrent transaction"
            ) from None
        return existing, False
