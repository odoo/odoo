from typing import Any

from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request
from odoo.service.model import call_kw
from odoo.service.server import thread_local

from .utils import clean_action


class DataSet(http.Controller):
    def _call_kw_readonly(self, rule: Any, args: Any) -> bool:
        params = request.get_json_data()["params"]
        try:
            model_class = request.registry[params["model"]]
        except KeyError as e:
            raise NotFound from e
        method_name = params["method"]
        for cls in model_class.mro():
            method = getattr(cls, method_name, None)
            if method is not None and hasattr(method, "_readonly"):
                return method._readonly
        return False

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
        if path != f"{model}.{method}":
            thread_local.rpc_model_method = f"{model}.{method}"
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
        if path != f"{model}.{method}":
            thread_local.rpc_model_method = f"{model}.{method}"
        action = call_kw(request.env[model], method, args, kwargs)
        # type="" is a sentinel meaning "no action"; absent type gets defaulted to act_window_close
        if isinstance(action, dict) and action.get("type") != "":
            return clean_action(action, env=request.env)
        return False
