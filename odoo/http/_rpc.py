import contextlib
from collections.abc import Callable, Sequence
from typing import Any

import odoo.service.common
import odoo.service.db
import odoo.service.model
from odoo.libs.debug_log import DebugLog
from odoo.libs.worker_thread import current_worker_thread

from .core import borrow_request

_debug = DebugLog(__name__)


def _get_rpc_dispatcher(service_name: str) -> Callable:
    match service_name:
        case "common":
            return odoo.service.common.dispatch
        case "db":
            return odoo.service.db.dispatch
        case "object":
            return odoo.service.model.dispatch
        case _:
            _debug.logic("http.dispatch_rpc.unknown_service", service=service_name)
            raise KeyError(service_name)


def _restore_thread_attr(thread: Any, attr: str, prev: Any, sentinel: Any) -> None:
    if prev is sentinel:
        with contextlib.suppress(AttributeError):
            delattr(thread, attr)
    else:
        setattr(thread, attr, prev)


def dispatch_rpc(service_name: str, method: str, params: Sequence[Any]) -> Any:
    thread = current_worker_thread()
    sentinel = object()
    prev_uid = getattr(thread, "uid", sentinel)
    prev_dbname = getattr(thread, "dbname", sentinel)
    with borrow_request():
        thread.uid = None
        thread.dbname = None
        _debug.pipeline(
            "http.dispatch_rpc.begin",
            service=service_name,
            method=method,
            params=len(params),
        )
        try:
            dispatch = _get_rpc_dispatcher(service_name)
            with _debug.perf("http.dispatch_rpc", service=service_name, method=method):
                return dispatch(method, params)
        finally:
            _restore_thread_attr(thread, "uid", prev_uid, sentinel)
            _restore_thread_attr(thread, "dbname", prev_dbname, sentinel)
