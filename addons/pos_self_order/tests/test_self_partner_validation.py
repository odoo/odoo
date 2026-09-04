
import json
from uuid import uuid4

import odoo.tests

from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest


class SelfPartnerValidationChecks:
    SELF_ORDERING_MODE = None

    def setUp(self):
        super().setUp()
        self.pos_config.write({"self_ordering_mode": self.SELF_ORDERING_MODE})
        self.pos_config.open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self.existing_partner = self.env["res.partner"].create({
            "name": "Demo",
            "email": "demo@example.com",
        })

    def test_validate_partner_creates_and_signs_a_new_partner(self):
        signed = self._validate_partner()
        self.assertIsInstance(signed, str)
        self.assertIn("-", signed)

        partner = self.env["res.partner"].browse(int(signed.split("-")[0]))
        self.assertTrue(partner.exists())
        self.assertEqual(partner.name, "User Self")
        self.assertEqual(partner.company_id, self.pos_config.company_id)
        self.assertEqual(self._resolve(signed), partner)

    def test_validate_partner_accepts_a_previously_signed_token(self):
        signed = self._validate_partner()
        partner_id = int(signed.split("-")[0])

        echoed = self._validate_partner(partner_id=signed)
        self.assertEqual(echoed, signed)
        self.assertEqual(self.env["res.partner"].search_count([("name", "=", "User Self")]), 1)
        self.assertTrue(self.env["res.partner"].browse(partner_id).exists())

    def test_validate_partner_ignores_a_raw_partner_id(self):
        before = set(self.env["res.partner"].search([]).ids)
        signed = self._validate_partner(partner_id=str(self.existing_partner.id))
        new_id = int(signed.split("-")[0])
        self.assertNotEqual(new_id, self.existing_partner.id)
        self.assertNotIn(new_id, before)

    def test_validate_partner_ignores_a_forged_signature(self):
        forged = f"{self.existing_partner.id}-{'0' * 64}"
        self.assertFalse(self._resolve(forged))

        signed = self._validate_partner(partner_id=forged)
        self.assertNotEqual(int(signed.split("-")[0]), self.existing_partner.id)

    def test_resolve_rejects_a_token_signed_for_another_partner(self):
        signed = self._validate_partner()
        signature = signed.split("-", 1)[1]
        tampered = f"{self.existing_partner.id}-{signature}"
        self.assertFalse(self._resolve(tampered))

    def test_resolve_rejects_malformed_tokens(self):
        for value in (False, "", "abc-def", "-", "42"):
            self.assertFalse(self._resolve(value), value)

    def test_token_is_scoped_to_the_config(self):
        other_config = self.pos_config.copy()
        signed = self._validate_partner()
        self.assertTrue(self._resolve(signed))
        self.assertFalse(self._resolve(signed, pos_config=other_config))

    def test_process_order_drops_an_unauthorized_partner(self):
        order = self._process_order(partner_id=str(self.existing_partner.id))
        self.assertFalse(order.partner_id)

    def test_process_order_drops_a_forged_partner_token(self):
        order = self._process_order(partner_id=f"{self.existing_partner.id}-{'0' * 64}")
        self.assertFalse(order.partner_id)

    def test_process_order_links_a_validated_partner(self):
        signed = self._validate_partner()
        expected = self.env["res.partner"].browse(int(signed.split("-")[0]))
        order = self._process_order(partner_id=signed)
        self.assertEqual(order.partner_id, expected)

    def test_process_order_without_partner(self):
        order = self._process_order()
        self.assertFalse(order.partner_id)

    # Helpers
    def _rpc(self, url, params):
        response = self.url_open(
            url,
            data=json.dumps({
                "jsonrpc": "2.0",
                "method": "call",
                "id": str(uuid4()),
                "params": params,
            }),
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        return response.json()

    def _validate_partner(self, **overrides):
        params = {
            "access_token": self.pos_config.access_token,
            "name": "User Self",
            "phone": "+3212345678",
            "email": "user.self@example.com",
            "street": "1 Test Street",
            "zip": "1000",
            "city": "Bxl",
            "country_id": self.env.ref("base.be").id,
        }
        params.update(overrides)
        result = self._rpc("/pos-self-order/validate-partner", params)
        self.assertNotIn("error", result, result.get("error"))
        return result["result"]["res.partner"][0]["id"]

    def _resolve(self, signed, pos_config=None):
        return self.env["pos.order"]._get_self_partner_from_token(pos_config or self.pos_config, signed)

    def _process_order(self, partner_id=None):
        order = {
            "config_id": self.pos_config.id,
            "session_id": self.pos_config.current_session_id.id,
            "state": "draft",
            "preset_id": self.out_preset.id,
            "amount_total": 0,
            "amount_tax": 0,
            "amount_paid": 0,
            "amount_return": 0,
            "lines": [],
            "tracking_number": None,
            "uuid": str(uuid4()),
        }
        if partner_id is not None:
            order["partner_id"] = partner_id

        result = self._rpc(f"/pos-self-order/process-order/{self.SELF_ORDERING_MODE}", {
            "access_token": self.pos_config.access_token,
            "order": order,
            "table_identifier": None,
        })
        self.assertNotIn("error", result, result.get("error"))
        order_id = result["result"]["pos.order"][0]["id"]
        return self.env["pos.order"].browse(order_id)


@odoo.tests.tagged("post_install", "-at_install")
class TestSelfPartnerValidationMobile(SelfPartnerValidationChecks, SelfOrderCommonTest):
    SELF_ORDERING_MODE = "mobile"


@odoo.tests.tagged("post_install", "-at_install")
class TestSelfPartnerValidationKiosk(SelfPartnerValidationChecks, SelfOrderCommonTest):
    SELF_ORDERING_MODE = "kiosk"
