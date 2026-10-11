# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from uuid import uuid4

import odoo.tests

from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest
from odoo.tools import mute_logger


@odoo.tests.tagged("post_install", "-at_install")
class TestSelfOrderSiblingPtav(SelfOrderCommonTest):
    def setUp(self):
        super().setUp()

        self.pos_config.write({
            "self_ordering_mode": "mobile",
            "self_ordering_service_mode": "counter",
        })
        self.env.company.point_of_sale_update_stock_quantities = "real"
        self.tiered = self.env["product.product"].create({
            "name": "Tiered Product",
            "type": "consu",
            "is_storable": True,
            "available_in_pos": True,
            "self_order_available": True,
            "list_price": 1000.0,
            "taxes_id": False,
            "pos_categ_ids": [(4, self.env["pos.category"].search([], limit=1).id)],
        })
        tier_attribute = self.env["product.attribute"].create({
            "name": "Tier",
            "display_type": "radio",
            "create_variant": "always",
        })
        premium_val, budget_val, free_val = self.env["product.attribute.value"].create([
            {"name": "Premium", "attribute_id": tier_attribute.id},
            {"name": "Budget", "attribute_id": tier_attribute.id},
            {"name": "Free", "attribute_id": tier_attribute.id},
        ])
        self.env["product.template.attribute.line"].create({
            "product_tmpl_id": self.tiered.product_tmpl_id.id,
            "attribute_id": tier_attribute.id,
            "value_ids": [(6, 0, [premium_val.id, budget_val.id, free_val.id])],
        })

        ptavs = self.tiered.product_tmpl_id.attribute_line_ids.product_template_value_ids
        self.premium_ptav = ptavs.filtered(lambda p: p.product_attribute_value_id == premium_val)
        self.budget_ptav = ptavs.filtered(lambda p: p.product_attribute_value_id == budget_val)
        self.free_ptav = ptavs.filtered(lambda p: p.product_attribute_value_id == free_val)

        self.premium_ptav.price_extra = 0.0
        self.budget_ptav.price_extra = -900.0
        self.free_ptav.price_extra = -1000.0

        self.premium_variant = self.tiered.product_tmpl_id.product_variant_ids.filtered(
            lambda v: v.product_template_attribute_value_ids == self.premium_ptav
        )

        self.pos_config.open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")

    def _post_order_json(self, ptav_ids):
        """POST one self-order carrying the Premium variant plus the given PTAVs.

        Client-side prices are deliberately bogus (9999) to prove the server
        recomputes from scratch. Returns the JSON-RPC response.
        """
        order_uuid = str(uuid4())
        response = self.url_open(
            "/pos-self-order/process-order/mobile/",
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
                        "amount_total": 9999,
                        "amount_tax": 0,
                        "amount_paid": 0,
                        "amount_return": 0,
                        "takeaway": True,
                        "uuid": order_uuid,
                        "lines": [[0, 0, {
                            "product_id": self.premium_variant.id,
                            "qty": 1,
                            "price_unit": 9999,
                            "price_subtotal": 9999,
                            "price_subtotal_incl": 9999,
                            "price_extra": 9999,
                            "attribute_value_ids": [[4, ptav_id] for ptav_id in ptav_ids],
                            "uuid": str(uuid4()),
                        }]],
                    },
                    "table_identifier": None,
                },
            }),
            headers={"Content-Type": "application/json"},
        )
        return response.json()

    def _post_order(self, ptav_ids):
        order_id = self._post_order_json(ptav_ids)["result"]["pos.order"][0]["id"]
        return self.env["pos.order"].browse(order_id)

    def test_honest_order_is_charged_and_not_fulfilled(self):
        order = self._post_order([self.premium_ptav.id])

        self.assertEqual(len(order.lines), 1)
        self.assertEqual(order.lines.product_id, self.premium_variant)
        self.assertEqual(order.amount_total, 1000.0,
                         "server must recompute the honest line to the 1000 base price")
        self.assertEqual(order.state, "draft",
                         "a non-zero self-order must stay draft until paid")
        self.assertFalse(order.picking_ids,
                         "an unpaid order must not be fulfilled")

    def test_sibling_ptav_is_rejected_and_price_holds(self):
        order = self._post_order([self.premium_ptav.id, self.free_ptav.id])

        self.assertEqual(len(order.lines), 1)
        self.assertEqual(order.lines.product_id, self.premium_variant,
                         "line is still the Premium variant")
        self.assertNotIn(self.free_ptav, order.lines.attribute_value_ids,
                         "the sibling Free PTAV must not survive validation")
        self.assertEqual(order.amount_total, 1000.0,
                         "the rejected sibling can no longer collapse the price")
        self.assertEqual(order.state, "draft",
                         "a correctly-priced order stays draft until paid")
        self.assertFalse(order.payment_ids)
        self.assertFalse(order.picking_ids,
                         "no goods are released without payment")

    def test_multiple_no_variant_values_same_attribute_rejected(self):
        size_attribute = self.env["product.attribute"].create({
            "name": "Size",
            "display_type": "radio",
            "create_variant": "no_variant",
        })
        small_val, large_val = self.env["product.attribute.value"].create([
            {"name": "Small", "attribute_id": size_attribute.id},
            {"name": "Large", "attribute_id": size_attribute.id},
        ])
        self.env["product.template.attribute.line"].create({
            "product_tmpl_id": self.tiered.product_tmpl_id.id,
            "attribute_id": size_attribute.id,
            "value_ids": [(6, 0, [small_val.id, large_val.id])],
        })
        size_ptavs = self.tiered.product_tmpl_id.attribute_line_ids.filtered(
            lambda l: l.attribute_id == size_attribute
        ).product_template_value_ids

        with mute_logger("odoo.http"):
            response = self._post_order_json([self.premium_ptav.id, *size_ptavs.ids])
        self.assertEqual(response["error"]["data"]["name"], "odoo.exceptions.UserError")
        self.assertEqual(response["error"]["data"]["message"], "Invalid product configuration")
        self.assertFalse(self.env["pos.order"].search([("session_id", "=", self.pos_config.current_session_id.id)]),
                         "no order is created from an invalid configuration")

        order = self._post_order([self.premium_ptav.id, size_ptavs[0].id])
        self.assertEqual(order.lines.attribute_value_ids, self.premium_ptav | size_ptavs[0])
