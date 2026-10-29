# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from uuid import uuid4

import odoo.tests
from odoo.tools import mute_logger

from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest


@odoo.tests.tagged("post_install", "-at_install")
class TestSelfOrderSiblingPtav(SelfOrderCommonTest):
    def setUp(self):
        super().setUp()

        self.pos_config.write({
            "self_ordering_mode": "mobile",
            "self_ordering_service_mode": "counter",
        })
        self.tiered = self.env["product.template"].create({
            "name": "Tiered Product",
            "type": "consu",
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
            "product_tmpl_id": self.tiered.id,
            "attribute_id": tier_attribute.id,
            "value_ids": [(6, 0, [premium_val.id, budget_val.id, free_val.id])],
        })

        ptavs = self.tiered.attribute_line_ids.product_template_value_ids
        self.premium_ptav = ptavs.filtered(lambda p: p.product_attribute_value_id == premium_val)
        self.budget_ptav = ptavs.filtered(lambda p: p.product_attribute_value_id == budget_val)
        self.free_ptav = ptavs.filtered(lambda p: p.product_attribute_value_id == free_val)

        self.premium_ptav.price_extra = 0.0
        self.budget_ptav.price_extra = -900.0
        self.free_ptav.price_extra = -1000.0

        self.premium_variant = self.tiered.product_variant_ids.filtered(
            lambda v: v.product_template_attribute_value_ids == self.premium_ptav,
        )

        self.pos_config.open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")

    def _post_order_json(self, ptav_ids, product=None):
        return self._post_lines_json([(product or self.premium_variant, 1, ptav_ids)])

    def _post_lines_json(self, lines):
        return self._post_commands_json(str(uuid4()), [[0, 0, {
            "product_id": product.id,
            "qty": qty,
            "attribute_value_ids": ptav_ids,
            "uuid": str(uuid4()),
        }] for product, qty, ptav_ids in lines])

    def _post_commands_json(self, order_uuid, line_commands, order_vals=None):
        for command in line_commands:
            command[2].update({
                "price_unit": 9999,
                "price_subtotal": 9999,
                "price_subtotal_incl": 9999,
                "price_extra": 9999,
            })
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
                        "preset_id": self.out_preset.id,
                        "uuid": order_uuid,
                        "lines": line_commands,
                        **(order_vals or {}),
                    },
                    "table_identifier": None,
                },
            }),
            headers={"Content-Type": "application/json"},
        )
        return response.json()

    def _post_order(self, ptav_ids, product=None):
        order_id = self._post_order_json(ptav_ids, product)["result"]["pos.order"][0]["id"]
        return self.env["pos.order"].browse(order_id)

    def test_honest_order_is_charged_and_not_paid(self):
        order = self._post_order([self.premium_ptav.id])

        self.assertEqual(len(order.lines), 1)
        self.assertEqual(order.lines.product_id, self.premium_variant)
        self.assertEqual(order.amount_total, 1000.0,
                         "server must recompute the honest line to the 1000 base price")
        self.assertEqual(order.state, "draft",
                         "a non-zero self-order must stay draft until paid")

    def test_sibling_ptav_is_rejected(self):
        with mute_logger("odoo.http"):
            response = self._post_order_json([self.premium_ptav.id, self.free_ptav.id])
        self.assertEqual(response["error"]["data"]["name"], "odoo.exceptions.UserError")
        self.assertEqual(response["error"]["data"]["message"], "Invalid product attribute")
        self.assertFalse(self.env["pos.order"].search([("session_id", "=", self.pos_config.current_session_id.id)]),
                         "no order is created, paid or fulfilled")

    def test_rejected_order_does_not_consume_sequence(self):
        sequence = self.pos_config.order_backend_seq_id
        next_number = sequence.number_next_actual
        with mute_logger("odoo.http"):
            response = self._post_order_json([self.premium_ptav.id, self.free_ptav.id])
        self.assertIn("error", response)

        sequence.invalidate_recordset(["number_next_actual"])
        self.assertEqual(sequence.number_next_actual, next_number)

    def test_archived_no_variant_value_kept_on_existing_line(self):
        option_attribute = self.env["product.attribute"].create({
            "name": "Option",
            "display_type": "radio",
            "create_variant": "no_variant",
        })
        extra_val, plain_val = self.env["product.attribute.value"].create([
            {"name": "Extra", "attribute_id": option_attribute.id},
            {"name": "Plain", "attribute_id": option_attribute.id},
        ])
        self.env["product.template.attribute.line"].create({
            "product_tmpl_id": self.tiered.id,
            "attribute_id": option_attribute.id,
            "value_ids": [(6, 0, [extra_val.id, plain_val.id])],
        })
        option_line = self.tiered.attribute_line_ids.filtered(
            lambda al: al.attribute_id == option_attribute,
        )
        extra_ptav = option_line.product_template_value_ids.filtered(lambda p: p.product_attribute_value_id == extra_val)
        extra_ptav.price_extra = 50.0
        ptav_ids = [self.premium_ptav.id, extra_ptav.id]

        order_uuid = str(uuid4())
        response = self._post_commands_json(order_uuid, [[0, 0, {
            "product_id": self.premium_variant.id,
            "qty": 1,
            "attribute_value_ids": ptav_ids,
            "uuid": str(uuid4()),
        }]])
        order = self.env["pos.order"].browse(response["result"]["pos.order"][0]["id"])
        line = order.lines
        self.assertEqual(order.amount_total, 1050.0)

        extra_ptav.ptav_active = False

        self._post_commands_json(order_uuid, [[1, line.id, {
            "product_id": self.premium_variant.id,
            "qty": 2,
            "attribute_value_ids": ptav_ids,
            "uuid": line.uuid,
        }]], {"id": order.id})
        self.assertEqual(line.attribute_value_ids, self.premium_ptav | extra_ptav,
                         "the archived value stays on the line it was ordered with")
        self.assertEqual(order.amount_total, 2100.0)

        with mute_logger("odoo.http"):
            response = self._post_lines_json([(self.premium_variant, 1, ptav_ids)])
        self.assertEqual(response["error"]["data"]["message"], "Invalid product attribute",
                         "an archived value cannot be ordered on a new line")

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
            "product_tmpl_id": self.tiered.id,
            "attribute_id": size_attribute.id,
            "value_ids": [(6, 0, [small_val.id, large_val.id])],
        })
        size_ptavs = self.tiered.attribute_line_ids.filtered(
            lambda al: al.attribute_id == size_attribute,
        ).product_template_value_ids

        with mute_logger("odoo.http"):
            response = self._post_order_json([self.premium_ptav.id, *size_ptavs.ids])
        self.assertEqual(response["error"]["data"]["name"], "odoo.exceptions.UserError")
        self.assertEqual(response["error"]["data"]["message"], "Invalid product configuration")
        self.assertFalse(self.env["pos.order"].search([("session_id", "=", self.pos_config.current_session_id.id)]),
                         "no order is created from an invalid configuration")

        order = self._post_order([self.premium_ptav.id, size_ptavs[0].id])
        self.assertEqual(order.lines.attribute_value_ids, self.premium_ptav | size_ptavs[0])

    def test_excluded_no_variant_value_rejected(self):
        option_attribute = self.env["product.attribute"].create({
            "name": "Option",
            "display_type": "radio",
            "create_variant": "no_variant",
        })
        standard_val, discount_val = self.env["product.attribute.value"].create([
            {"name": "Standard", "attribute_id": option_attribute.id},
            {"name": "Free Discount", "attribute_id": option_attribute.id},
        ])
        self.env["product.template.attribute.line"].create({
            "product_tmpl_id": self.tiered.id,
            "attribute_id": option_attribute.id,
            "value_ids": [(6, 0, [standard_val.id, discount_val.id])],
        })
        option_ptavs = self.tiered.attribute_line_ids.filtered(
            lambda al: al.attribute_id == option_attribute,
        ).product_template_value_ids
        discount_ptav = option_ptavs.filtered(lambda p: p.product_attribute_value_id == discount_val)
        discount_ptav.write({
            "price_extra": -50.0,
            "excluded_value_ids": [(6, 0, self.premium_ptav.ids)],
        })

        with mute_logger("odoo.http"):
            response = self._post_order_json([self.premium_ptav.id, discount_ptav.id])
        self.assertEqual(response["error"]["data"]["name"], "odoo.exceptions.UserError")
        self.assertEqual(response["error"]["data"]["message"], "Invalid product configuration")
        self.assertFalse(self.env["pos.order"].search([("session_id", "=", self.pos_config.current_session_id.id)]),
                         "no order is created from an excluded combination")

        # The exclusion only targets Premium: the same value stays orderable on Budget.
        budget_variant = self.tiered.product_variant_ids.filtered(
            lambda v: v.product_template_attribute_value_ids == self.budget_ptav,
        )
        order = self._post_order([self.budget_ptav.id, discount_ptav.id], budget_variant)
        self.assertEqual(order.lines.attribute_value_ids, self.budget_ptav | discount_ptav)
        self.assertEqual(order.amount_total, 50.0)

    def test_negative_line_cannot_offset_another_line(self):
        option_attribute = self.env["product.attribute"].create({
            "name": "Option",
            "display_type": "radio",
            "create_variant": "no_variant",
        })
        discount_val = self.env["product.attribute.value"].create({
            "name": "Discount",
            "attribute_id": option_attribute.id,
        })
        self.env["product.template.attribute.line"].create({
            "product_tmpl_id": self.tiered.id,
            "attribute_id": option_attribute.id,
            "value_ids": [(6, 0, discount_val.ids)],
        })
        discount_ptav = self.tiered.attribute_line_ids.filtered(
            lambda al: al.attribute_id == option_attribute,
        ).product_template_value_ids
        discount_ptav.write({
            "price_extra": -1100.0,
            "excluded_value_ids": [(6, 0, self.premium_ptav.ids)],
        })
        budget_variant = self.tiered.product_variant_ids.filtered(
            lambda v: v.product_template_attribute_value_ids == self.budget_ptav,
        )

        with mute_logger("odoo.http"):
            response = self._post_lines_json([
                (self.premium_variant, 1, [self.premium_ptav.id]),
                (budget_variant, 1, [self.budget_ptav.id, discount_ptav.id]),
            ])
        self.assertEqual(response["error"]["data"]["name"], "odoo.exceptions.UserError")
        self.assertEqual(response["error"]["data"]["message"], "Invalid product configuration")
        self.assertFalse(self.env["pos.order"].search([("session_id", "=", self.pos_config.current_session_id.id)]),
                         "no order is created, paid or fulfilled")
