import json

from odoo import http
from odoo.http import request
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class TestsSharedJsPython(http.Controller):
    @http.route(
        "/account/init_tests_shared_js_python", type="http", auth="user", website=True
    )
    def route_init_tests_shared_js_python(self):
        _debug.pipeline(
            "route", handler="TestsSharedJsPython.route_init_tests_shared_js_python"
        )
        tests = json.loads(
            request.env["ir.config_parameter"]
            .sudo()
            .get_param("account.tests_shared_js_python", "[]")
        )
        return request.render(
            "account.tests_shared_js_python", {"props": {"tests": tests}}
        )

    @http.route("/account/post_tests_shared_js_python", type="jsonrpc", auth="user")
    def route_post_tests_shared_js_python(self, results):
        _debug.pipeline(
            "route", handler="TestsSharedJsPython.route_post_tests_shared_js_python"
        )
        request.env["ir.config_parameter"].sudo().set_param(
            "account.tests_shared_js_python", json.dumps(results or [])
        )
