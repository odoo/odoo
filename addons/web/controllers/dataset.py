import threading
from typing import Any

from odoo import api, http
from odoo.http import NotFound, request
from odoo.service.model import call_kw

from ..tools import debug_log as dbg
from .utils import clean_action


def _tag_thread_with_rpc_target(model: str, method: str, path: str | None) -> None:
    if path != f"{model}.{method}":
        threading.current_thread().rpc_model_method = f"{model}.{method}"


class DataSet(http.Controller):
    def _call_kw_readonly(self, rule: Any, args: Any) -> bool:
        try:
            params = request.get_json_data()["params"]
            model_class = request.registry[params["model"]]
            method_name = params["method"]
        except KeyError as e:
            dbg.logic.debug("[rpc] readonly probe: malformed params (%s)", e)
            raise NotFound from e
        readonly = api.is_readonly(model_class, method_name)
        dbg.logic.debug(
            "[rpc:%s.%s] readonly=%s", params["model"], method_name, readonly
        )
        return readonly

    @http.route(
        ["/web/dataset/call_kw", "/web/dataset/call_kw/<path:path>"],
        type="jsonrpc",
        auth="user",
        readonly=_call_kw_readonly,
    )
    def call_kw(
        self,
        model: str,
        method: str,
        args: list[Any],
        kwargs: dict[str, Any],
        path: str | None = None,
    ) -> Any:
        dbg.lifecycle.debug(
            "[rpc:%s.%s] call_kw: %s args=%d kwargs=%s path_match=%s",
            model,
            method,
            dbg.req(),
            len(args),
            dbg.keys(kwargs),
            path == f"{model}.{method}",
        )
        _tag_thread_with_rpc_target(model, method, path)
        with dbg.timer(request.env, "[rpc:%s.%s] call_kw", model, method):
            return call_kw(request.env[model], method, args, kwargs)

    @http.route(
        ["/web/dataset/call_button", "/web/dataset/call_button/<path:path>"],
        type="jsonrpc",
        auth="user",
        readonly=_call_kw_readonly,
    )
    def call_button(
        self,
        model: str,
        method: str,
        args: list[Any],
        kwargs: dict[str, Any],
        path: str | None = None,
    ) -> dict[str, Any] | bool:
        dbg.lifecycle.debug(
            "[rpc:%s.%s] call_button: %s args=%d kwargs=%s",
            model,
            method,
            dbg.req(),
            len(args),
            dbg.keys(kwargs),
        )
        _tag_thread_with_rpc_target(model, method, path)
        with dbg.timer(request.env, "[rpc:%s.%s] call_button", model, method):
            action = call_kw(request.env[model], method, args, kwargs)
        if isinstance(action, dict) and action.get("type") != "":
            dbg.pipeline.debug(
                "[rpc:%s.%s] call_button -> action %s",
                model,
                method,
                action.get("type"),
            )
            return clean_action(action, env=request.env)
        dbg.logic.debug(
            "[rpc:%s.%s] call_button -> no action (%s)",
            model,
            method,
            type(action).__name__,
        )
        return False
