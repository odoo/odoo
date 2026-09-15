from __future__ import annotations

import logging
import os
import signal
from typing import TYPE_CHECKING, Any

import psutil

from odoo.libs.debug_log import DebugLog

from ._limits import get_memory_over_soft_limit
from .settings import ServerSettings, current

if TYPE_CHECKING:
    from collections.abc import Callable

_SIGHUP_AVAILABLE = hasattr(signal, "SIGHUP")

_logger = logging.getLogger("odoo.service.server")
_debug = DebugLog(__name__)


_on_stop_hooks: list[Callable] = []
"""What to run when THIS PROCESS's server stops.  Process-wide, not per class.

A process runs one server, and a hook registered by (say) the sass compiler has
no opinion about which flavour is running, so a module-level list is the right
shape.  What was misleading was reaching it only through `CommonServer.register_on_stop_hook`,
a `@classmethod`, which reads as class state.  Verified, not inferred: one hook
registered on `CommonServer` ran on `stop()` for two unrelated subclasses, and
was still registered afterwards.  So the storage and the functions that touch it
live together here, and `CommonServer.register_on_stop_hook` is the alias two callers outside
`service/` already import (`tools/sass_embedded.py`, `tools/assets/esm_lexer.py`).

There is deliberately no unregister.  Nothing in production wants one, and the
only real consequence -- a test leaving a hook behind for every later test in the
process -- is now caught by the leak guard in `tests/service/conftest.py`, which
watches this list.
"""


def register_on_stop_hook(func: Callable) -> None:
    if func not in _on_stop_hooks:
        _on_stop_hooks.append(func)
        _debug.lifecycle(
            "server.stop_hook.registered",
            hook=getattr(func, "__qualname__", None),
            hooks=len(_on_stop_hooks),
        )


def run_on_stop_hooks(logger: logging.Logger) -> None:
    _debug.pipeline("server.stop_hooks.run", hooks=len(_on_stop_hooks))
    for func in _on_stop_hooks:
        try:
            logger.debug("on_close call %s", func)
            with _debug.perf(
                "server.stop_hook.ran", hook=getattr(func, "__qualname__", None)
            ):
                func()
        except Exception:
            name = getattr(func, "__name__", repr(func))
            logger.warning("Exception in %s", name, exc_info=True)
            _debug.logic("server.stop_hook.failed", hook=name)


class CommonServer:
    is_reload_watcher_owner = True
    flavor = "unknown"
    """How this server names itself to an operator, a metric, an alert.

    A class attribute rather than a lookup keyed on the class name: a new
    server flavour that forgets to set it is answering "unknown", which is
    visible, where a name-keyed dict outside the class answers with the class
    name and is not.
    """
    port_setting = "http_port"

    def __init__(self, app: Any) -> None:
        self.app = app
        self.interface: str = self.settings.http_interface or "0.0.0.0"
        self.port: int = getattr(self.settings, self.port_setting)
        self.pid: int = os.getpid()
        self.logger = _logger.getChild(self.__class__.__name__)
        self._process_handle = psutil.Process(self.pid)
        _debug.lifecycle(
            "server.created",
            flavor=self.flavor,
            interface=self.interface,
            port=self.port,
            pid=self.pid,
        )

    @property
    def settings(self) -> ServerSettings:
        return current()

    def run(self, preload: list[str] | None = None, stop: bool = False) -> int | None:
        raise NotImplementedError(
            f"{type(self).__name__} does not implement run(); every concrete "
            f"server flavour has to"
        )

    def get_metrics(self) -> dict[str, Any]:
        return {}

    def get_memory_over_soft_limit(self) -> int | None:
        limit = self.get_memory_soft_limit()
        memory = get_memory_over_soft_limit(self._process_handle, limit)
        if memory is not None:
            self.logger.warning("RSS memory soft-limit reached: %s bytes.", memory)
            _debug.logic(
                "server.memory_soft_limit_exceeded",
                flavor=self.flavor,
                rss=memory,
                limit=limit,
            )
        return memory

    def get_memory_soft_limit(self) -> int:
        return self.settings.limit_memory_soft

    @classmethod
    def register_on_stop_hook(cls, func: Callable) -> None:
        register_on_stop_hook(func)

    def stop(self) -> None:
        _debug.lifecycle(
            "server.stopping", flavor=self.flavor, pid=getattr(self, "pid", None)
        )
        run_on_stop_hooks(self.logger)
