# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from uuid import uuid4

import odoo.tests
from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest
from odoo.fields import Command
from odoo.tools import mute_logger


@odoo.tests.tagged("post_install", "-at_install")
class TestSelfOrderLoyalty(SelfOrderCommonTest):
    """
    A malicious self-order client can send any reward_id/product_id/card_id combination
    it likes in the order payload: these tests simulate that by posting a hand-crafted
    JSON-RPC body directly to the process-order controller (bypassing the trusted JS
    layer entirely), the same way test_self_order_combo.py proves combo tampering is
    refused. A browser tour can't express this: it only ever sends payloads the real
    frontend code is capable of building.
    """

    def setUp(self):
        super().setUp()
        self.pos_config.write({
            'self_ordering_mode': 'kiosk',
            'available_preset_ids': [(5, 0)],
            'use_presets': False,
        })
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")

        self.loyalty_partner = self.env['res.partner'].create({'name': 'Loyalty Customer'})
        self.other_partner = self.env['res.partner'].create({'name': 'Someone Else'})

        self.program = self.env['loyalty.program'].create({
            'name': 'Free Product Program',
            'program_type': 'loyalty',
            'trigger': 'auto',
            'applies_on': 'both',
            'rule_ids': [Command.create({
                'reward_point_amount': 1,
                'reward_point_mode': 'order',
                'minimum_qty': 1,
            })],
            'reward_ids': [Command.create({
                'reward_type': 'product',
                'reward_product_id': self.free.id,
                'reward_product_qty': 1,
                'required_points': 200,
            })],
        })
        self.reward = self.program.reward_ids[:1]

    def _post_self_order(self, lines):
        """Send a raw order payload on the public self-order endpoint."""
        order_uuid = str(uuid4())
        response = self.url_open(
            "/pos-self-order/process-order/kiosk",
            headers={"Content-Type": "application/json"},
            data=json.dumps({
                "jsonrpc": "2.0",
                "method": "call",
                "id": str(uuid4()),
                "params": {
                    "access_token": self.pos_config.access_token,
                    "table_identifier": None,
                    "order": {
                        "id": None,
                        "session_id": self.pos_config.current_session_id.id,
                        "state": "draft",
                        "preset_id": False,
                        "amount_total": 0,
                        "amount_tax": 0,
                        "amount_paid": 0,
                        "amount_return": 0,
                        "uuid": order_uuid,
                        "partner_id": self.loyalty_partner.id,
                        "lines": lines,
                    },
                },
            }),
        )
        return response.json(), order_uuid

    def _reward_line(self, product, reward, card=False, points_cost=0):
        return [Command.CREATE, 0, {
            "uuid": str(uuid4()),
            "product_id": product.id,
            "qty": 1,
            "price_unit": 0,
            "price_subtotal": 0,
            "price_subtotal_incl": 0,
            "is_reward_line": True,
            "reward_id": reward.id,
            "card_id": card.id if card else False,
            "points_cost": points_cost,
        }]

    @mute_logger('odoo.http')
    def test_reward_with_wrong_product_is_refused(self):
        """
        A reward line claiming a product the reward doesn't grant (e.g. pairing a cheap
        reward's id with an unrelated, possibly expensive, product) must be refused.
        """
        card = self.env['loyalty.card'].create({
            'program_id': self.program.id,
            'partner_id': self.loyalty_partner.id,
            'points': 500,
        })
        result, order_uuid = self._post_self_order([
            self._reward_line(self.desk_organizer, self.reward, card, points_cost=1),
        ])
        self.assertIn('error', result, "A reward line claiming a product it doesn't grant must be refused")
        self.assertFalse(self.env['pos.order'].search([('uuid', '=', order_uuid)]),
            msg="The refused order must not be created")

    @mute_logger('odoo.http')
    def test_reward_from_unavailable_program_is_refused(self):
        """A reward from a program not available to this pos.config must be refused."""
        other_config = self.env['pos.config'].create({'name': 'Other Config'})
        foreign_program = self.env['loyalty.program'].create({
            'name': 'Foreign Program',
            'program_type': 'loyalty',
            'trigger': 'auto',
            'applies_on': 'both',
            'pos_config_ids': [Command.link(other_config.id)],
            'reward_ids': [Command.create({
                'reward_type': 'product',
                'reward_product_id': self.free.id,
                'reward_product_qty': 1,
                'required_points': 1,
            })],
        })
        foreign_reward = foreign_program.reward_ids[:1]
        card = self.env['loyalty.card'].create({
            'program_id': foreign_program.id,
            'partner_id': self.loyalty_partner.id,
            'points': 500,
        })
        result, order_uuid = self._post_self_order([
            self._reward_line(self.free, foreign_reward, card, points_cost=1),
        ])
        self.assertIn('error', result, "A reward from a program unavailable to this POS must be refused")
        self.assertFalse(self.env['pos.order'].search([('uuid', '=', order_uuid)]),
            msg="The refused order must not be created")

    @mute_logger('odoo.http')
    def test_reward_card_of_another_partner_is_refused(self):
        """A nominative card reserved for a different partner must not be spendable here."""
        card = self.env['loyalty.card'].create({
            'program_id': self.program.id,
            'partner_id': self.other_partner.id,
            'points': 500,
        })
        result, order_uuid = self._post_self_order([
            self._reward_line(self.free, self.reward, card, points_cost=1),
        ])
        self.assertIn('error', result, "A card reserved for a different partner must be refused")
        self.assertFalse(self.env['pos.order'].search([('uuid', '=', order_uuid)]),
            msg="The refused order must not be created")

    @mute_logger('odoo.http')
    def test_insufficient_points_is_refused(self):
        """
        The reward/product/card combination is legitimate here, so the self-order-specific
        check lets it through. The order must still be blocked because the card cannot
        cover the reward's point cost: this is enforced by _process_loyalty(), which runs
        synchronously within the same request since the order (a single free-product
        reward line) totals 0 and is auto-paid by the controller.
        """
        card = self.env['loyalty.card'].create({
            'program_id': self.program.id,
            'partner_id': self.loyalty_partner.id,
            'points': 0,  # far below the reward's 200 required_points
        })
        result, order_uuid = self._post_self_order([
            self._reward_line(self.free, self.reward, card, points_cost=1),
        ])
        self.assertIn('error', result, "A reward the card cannot afford must be refused")
        self.assertFalse(self.env['pos.order'].search([('uuid', '=', order_uuid)]),
            msg="The refused order must not be created")
        card.invalidate_recordset()
        self.assertEqual(card.points, 0, "The card must not have been debited")

    @mute_logger('odoo.http')
    def test_valid_reward_claim_is_accepted(self):
        """A legitimate reward claim, from a card with enough points, must go through."""
        card = self.env['loyalty.card'].create({
            'program_id': self.program.id,
            'partner_id': self.loyalty_partner.id,
            'points': 500,
        })
        result, order_uuid = self._post_self_order([
            self._reward_line(self.free, self.reward, card, points_cost=1),
        ])
        self.assertNotIn('error', result, result.get('error'))
        order = self.env['pos.order'].search([('uuid', '=', order_uuid)])
        self.assertTrue(order.exists())
        self.assertEqual(order.state, 'paid', "A free reward order must be auto-paid")

        reward_line = order.lines.filtered('is_reward_line')
        self.assertEqual(reward_line.product_id, self.free)
        self.assertEqual(reward_line.price_unit, 0.0, "The free product reward line must stay priced at 0")

        card.invalidate_recordset()
        self.assertEqual(card.points, 300.0, "500 preloaded - 200 required points for the reward")
