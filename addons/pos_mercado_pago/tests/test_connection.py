from unittest.mock import patch

import requests
from requests import Response

from odoo.libs.guarded_http import GuardedSession
from odoo.tests.common import tagged

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.addons.pos_mercado_pago.models.mercado_pago_pos_request import (
    MercadoPagoPosRequest,
)


@tagged("post_install", "-at_install")
class TestMercadoPagoConnection(TestPointOfSaleHttpCommon):
    def setUp(self):
        super().setUp()
        self.method = self.env["pos.payment.method"].create(
            {
                "name": "Mercado Pago connection",
                "use_payment_terminal": "mercado_pago",
                "payment_method_type": "terminal",
                "journal_id": self.bank_journal.id,
            }
        )

    def test_a_terminal_call_goes_through_its_connection(self):
        response = Response()
        response.status_code = 200
        response._content = b'{"id": "intent"}'
        with patch.object(GuardedSession, "request", return_value=response) as sent:
            result = MercadoPagoPosRequest(self.method, "token").call_mercado_pago(
                "get", "/point/integration-api/devices", {}
            )

        self.assertEqual(result, {"id": "intent"})
        self.assertEqual(sent.call_args.args[0], "GET")
        self.assertEqual(
            self.method._get_integration_connection().service_id.code,
            "pos_mercado_pago",
        )

    def test_an_unreachable_terminal_reads_as_an_error_message(self):
        with patch.object(
            GuardedSession, "request", side_effect=requests.ConnectionError("down")
        ):
            result = MercadoPagoPosRequest(self.method, "token").call_mercado_pago(
                "get", "/point/integration-api/devices", {}
            )

        self.assertIn("down", result["errorMessage"])
