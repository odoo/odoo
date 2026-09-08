from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestSmsController(HttpCase):
    """A malformed delivery-report payload to `/sms/status` must raise the
    intended `UserError`, not crash the route with an unrelated `TypeError`.
    """

    def test_malformed_webhook_payload_raises_user_error_not_type_error(self):
        # this route is `type="jsonrpc"`: `JsonRPCDispatcher.prepare_error_response`
        # always answers with HTTP 200 and a JSON-RPC `error` envelope, whatever
        # the underlying exception type -- so the externally observable
        # difference this bug causes is in the envelope's `error.data.name`,
        # not the HTTP status code.
        response = self.url_open(
            "/sms/status",
            data='{"jsonrpc": "2.0", "method": "call", "params": {"message_statuses": [{"uuids": [], "sms_status": "delivered"}]}}',
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 200)
        error = response.json()["error"]
        self.assertEqual(
            error["data"]["name"],
            "odoo.exceptions.UserError",
            "a malformed payload must surface as the intended UserError, not "
            "an unrelated TypeError from a bad UserError(...) call signature",
        )
