
import json
from uuid import uuid4

import odoo.tests

from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest


@odoo.tests.tagged("post_install", "-at_install")
class TestSelfOrderPartnerIgnored(SelfOrderCommonTest):
    def test_process_order_ignores_client_partner_id(self):
        self.pos_config.write({"self_ordering_mode": "mobile"})
        self.pos_config.open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")

        existing_partner = self.env["res.partner"].create({"name": "Customer"})

        response = self.url_open(
            "/pos-self-order/process-order/mobile",
            data=json.dumps({
                "jsonrpc": "2.0",
                "method": "call",
                "id": str(uuid4()),
                "params": {
                    "access_token": self.pos_config.access_token,
                    "order": {
                        "config_id": self.pos_config.id,
                        "session_id": self.pos_config.current_session_id.id,
                        "state": "draft",
                        "amount_total": 0,
                        "amount_tax": 0,
                        "amount_paid": 0,
                        "amount_return": 0,
                        "lines": [],
                        "takeaway": True,
                        "partner_id": existing_partner.id,
                        "uuid": str(uuid4()),
                    },
                    "table_identifier": None,
                },
            }),
            headers={"Content-Type": "application/json"},
        )

        result = response.json()
        order_id = result["result"]["pos.order"][0]["id"]
        order = self.env["pos.order"].browse(order_id)
        self.assertFalse(order.partner_id)
