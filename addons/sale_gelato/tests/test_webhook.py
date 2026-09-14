import json

from odoo.tests import HttpCase, tagged
from odoo.tools import mute_logger

from odoo.addons.sale_gelato.controlers.main import GelatoController


@tagged("post_install", "-at_install")
class TestGelatoWebhook(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.gelato_webhook_secret = "gelato-secret"
        partner = cls.env["res.partner"].create({"name": "Gelato buyer"})
        cls.order = cls.env["sale.order"].create({"partner_id": partner.id})

    def _post(self, order_id, signature):
        return self.url_open(
            GelatoController._webhook_url,
            data=json.dumps(
                {
                    "event": "order_status_updated",
                    "orderReferenceId": str(order_id),
                    "fulfillmentStatus": "delivered",
                }
            ),
            headers={"Content-Type": "application/json", "signature": signature},
        )

    @mute_logger("odoo.addons.sale_gelato.controlers.main", "odoo.http")
    def test_an_unknown_order_is_refused_and_logged(self):
        response = self._post(self.order.id + 100000, "gelato-secret")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            self.env["inbound.access.log"]
            .sudo()
            .search_count([("gate_model", "=", "sale.order"), ("gate_id", "=", 0)]),
            1,
        )

    @mute_logger(
        "odoo.addons.sale_gelato.controlers.main",
        "odoo.addons.integration.models.mixin_inbound_gate",
        "odoo.http",
    )
    def test_a_wrong_signature_is_refused(self):
        response = self._post(self.order.id, "forged")

        self.assertEqual(response.status_code, 403)

    def test_a_signed_update_is_admitted_through_the_company_receiver(self):
        response = self._post(self.order.id, "gelato-secret")

        self.assertEqual(response.status_code, 200)
        receiver = (
            self.env["integration.receiver"]
            .sudo()
            .search(
                [
                    ("res_model", "=", "res.company"),
                    ("res_id", "=", self.env.company.id),
                    ("res_purpose", "=", "gelato_webhook"),
                ]
            )
        )
        self.assertEqual(
            self.env["integration.exchange"]
            .sudo()
            .search([("channel_id", "=", f"integration.receiver,{receiver.id}")])
            .mapped("event_type"),
            ["gelato_order_status_updated"],
        )
