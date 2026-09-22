from odoo import http


class TestRpcController(http.Controller):
    @http.route("/test_rpc/echo_context_keys", type="jsonrpc", auth="user")
    def echo_context_keys(self, context=None):
        return sorted(context or {})
