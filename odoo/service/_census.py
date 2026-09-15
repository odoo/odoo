from __future__ import annotations

import contextlib
import json
import logging
import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from odoo.libs.debug_log import DebugLog

from .settings import current

_logger = logging.getLogger("odoo.service.server")
_debug = DebugLog(__name__)

CENSUS_WRITE_INTERVAL_S = 4.0
"""How often the master rewrites its census.  Matches the supervision beat."""

CENSUS_MAX_AGE_S = 60.0
"""Older than this and the census is not answered from; see `WorkerCensus.read`."""


class WorkerCensus:
    """The master's worker counts, published as a file its children can read.

    `/web/metrics` is served by a child, which cannot count its siblings; the
    file is the child's only route to the master's numbers.  Reads and writes
    raise on I/O trouble -- the caller decides how much it cares.
    """

    def __init__(self, pid: int) -> None:
        self.pid = pid
        self.written_at = float("-inf")

    @property
    def path(self) -> Path | None:
        data_dir = current().data_dir
        if not data_dir:
            return None
        return Path(data_dir) / f"prefork-census-{self.pid}.json"

    def publish(self, payload: Callable[[], dict[str, Any]]) -> bool:
        now = time.monotonic()
        if now - self.written_at < CENSUS_WRITE_INTERVAL_S:
            return False
        path = self.path
        if path is None:
            return False
        self.written_at = now
        tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
        try:
            tmp.write_text(json.dumps(payload()))
            tmp.replace(path)
        except Exception:
            with contextlib.suppress(OSError):
                tmp.unlink()
            raise
        _debug.pipeline("prefork.census_published", path=str(path))
        return True

    def read(self) -> dict[str, Any]:
        path = self.path
        if path is None:
            return {}
        try:
            if time.time() - path.stat().st_mtime > CENSUS_MAX_AGE_S:
                _debug.logic("prefork.census_stale", max_age_s=CENSUS_MAX_AGE_S)
                return {}
            payload = json.loads(path.read_text())
        except Exception:
            _debug.logic("prefork.census_unreadable", path=str(path))
            return {}
        return payload if isinstance(payload, dict) else {}

    def discard(self) -> None:
        path = self.path
        if path is not None:
            with contextlib.suppress(OSError):
                path.unlink()
            _debug.lifecycle("prefork.census_discarded", path=str(path))

    def remove_stale(self) -> None:
        path = self.path
        if path is None:
            return
        cutoff = time.time() - CENSUS_MAX_AGE_S
        try:
            for stale in path.parent.glob("prefork-census-*.json"):
                if stale != path and stale.stat().st_mtime < cutoff:
                    with contextlib.suppress(OSError):
                        stale.unlink()
                        _debug.lifecycle("prefork.census_removed", path=str(stale))
        except Exception:
            _logger.debug("Could not remove stale censuses", exc_info=True)


__all__ = ("CENSUS_MAX_AGE_S", "CENSUS_WRITE_INTERVAL_S", "WorkerCensus")
