from unittest.mock import patch

from requests import Response

from odoo.libs.guarded_http import GuardedSession
from odoo.tests.common import tagged

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


@tagged("post_install", "-at_install")
class TestAdyenPoS(TestPointOfSaleHttpCommon):
    def test_adyen_basic_order(self):
        self.main_pos_config.write(
            {
                "payment_method_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Adyen",
                            "use_payment_terminal": True,
                            "adyen_api_key": "my_adyen_api_key",
                            "adyen_terminal_identifier": "my_adyen_terminal",
                            "adyen_test_mode": False,
                            "use_payment_terminal": "adyen",
                            "payment_method_type": "terminal",
                            "journal_id": self.bank_journal.id,
                        },
                    ),
                ],
            }
        )
        self.main_pos_config.with_user(self.pos_user).open_ui()

        def post(session, method, url, **kwargs):
            # TODO: check that the data passed by pos to adyen is correct
            response = Response()
            response.status_code = 200
            response._content = b"ok"
            return response

        with (
            patch.object(GuardedSession, "request", post),
            patch("odoo.addons.pos_adyen.controllers.main.consteq", lambda a, b: True),
        ):
            self.start_pos_tour("PosAdyenTour")

    def test_the_terminal_calls_through_its_own_connection(self):
        method = self.env["pos.payment.method"].create(
            {
                "name": "Adyen connection",
                "use_payment_terminal": "adyen",
                "adyen_api_key": "my_adyen_api_key",
                "adyen_terminal_identifier": "my_adyen_connection_terminal",
                "payment_method_type": "terminal",
                "journal_id": self.bank_journal.id,
            }
        )
        response = Response()
        response.status_code = 200
        response._content = b"ok"

        with patch.object(GuardedSession, "request", return_value=response):
            method._proxy_adyen_request_direct({}, "terminal_request")
        self.env.flush_all()
        self.env.cr.precommit.run()

        connection = method._get_integration_connection()
        self.assertEqual(connection.service_id.code, "pos_adyen")
        self.assertTrue(
            self.env["integration.exchange"].sudo().search_count(
                [("connection_id", "=", connection.id)]
            )
        )
