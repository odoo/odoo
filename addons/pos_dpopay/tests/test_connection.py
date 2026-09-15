from unittest.mock import patch

from requests import Response

from odoo.libs.guarded_http import GuardedSession
from odoo.tests.common import tagged

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


@tagged("post_install", "-at_install")
class TestDpoPayConnection(TestPointOfSaleHttpCommon):
    def test_a_terminal_call_goes_through_its_connection(self):
        method = self.env["pos.payment.method"].create(
            {
                "name": "DPO Pay connection",
                "use_payment_terminal": "dpopay",
                "payment_method_type": "terminal",
                "journal_id": self.bank_journal.id,
                "dpopay_bearer_token": "bearer",
            }
        )
        response = Response()
        response.status_code = 200
        response._content = b'{"status": "ok"}'

        with patch.object(GuardedSession, "request", return_value=response) as sent:
            result = method._execute_dpopay_api_request({}, "get-status")

        self.assertEqual(result, {"status": "ok"})
        self.assertEqual(sent.call_args.args[0], "POST")
        self.env.flush_all()
        self.env.cr.precommit.run()
        connection = method._get_integration_connection()
        self.assertEqual(connection.service_id.code, "pos_dpopay")
        self.assertTrue(
            self.env["integration.exchange"]
            .sudo()
            .search_count([("connection_id", "=", connection.id)])
        )
