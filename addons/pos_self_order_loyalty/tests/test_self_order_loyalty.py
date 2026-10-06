# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import time
from unittest.mock import patch
from uuid import uuid4

import odoo.tests
from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest
from odoo.fields import Command
from odoo.tools import mute_logger

VALID_TOKEN = object()


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

    def _jsonrpc(self, url, params):
        response = self.url_open(
            url,
            headers={"Content-Type": "application/json"},
            data=json.dumps({
                "jsonrpc": "2.0",
                "method": "call",
                "id": str(uuid4()),
                "params": {"access_token": self.pos_config.access_token, **params},
            }),
        )
        return response.json()

    def _post_self_order(self, lines, partner=None, partner_token=VALID_TOKEN, order_id=None, order_uuid=None):
        """Send a raw order payload on the public self-order endpoint.

        By default the order is made for `loyalty_partner`, backed by a valid identification
        token, as the genuine frontend does once the customer identified.
        """
        partner = self.loyalty_partner if partner is None else partner
        if partner_token is VALID_TOKEN:
            partner_token = partner._get_self_order_token(self.pos_config) if partner else None
        order_uuid = order_uuid or str(uuid4())
        order = {
            "id": order_id,
            "session_id": self.pos_config.current_session_id.id,
            "state": "draft",
            "preset_id": False,
            "amount_total": 0,
            "amount_tax": 0,
            "amount_paid": 0,
            "amount_return": 0,
            "uuid": order_uuid,
            "partner_id": partner.id if partner else False,
            "lines": lines,
        }
        if partner_token:
            order["partner_token"] = partner_token
        result = self._jsonrpc("/pos-self-order/process-order/kiosk", {"table_identifier": None, "order": order})
        return result, order_uuid

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

    # cola: 2.2 excluded + 15% tax, 10 units = 25.30 tax included
    def _create_discount_program(self, **reward_values):
        return self.env['loyalty.program'].create({
            'name': 'Discount Program',
            'program_type': 'promotion',
            'trigger': 'auto',
            'applies_on': 'current',
            'rule_ids': [Command.create({
                'reward_point_amount': 1,
                'reward_point_mode': 'order',
                'minimum_qty': 1,
            })],
            'reward_ids': [Command.create({
                'reward_type': 'discount',
                'discount_applicability': 'order',
                'required_points': 1,
                **reward_values,
            })],
        })

    def _product_line(self, product, qty):
        return [Command.CREATE, 0, {
            "uuid": str(uuid4()),
            "product_id": product.id,
            "qty": qty,
            "price_unit": product.lst_price,
            "price_subtotal": 0,
            "price_subtotal_incl": 0,
            "tax_ids": self.default_tax15.ids,
        }]

    def _discount_line(self, reward, price_unit, taxes=None):
        line = self._reward_line(reward.discount_line_product_id, reward)
        line[2].update({
            "price_unit": price_unit,
            "tax_ids": (self.default_tax15 if taxes is None else taxes).ids,
        })
        return line

    def _assert_refused(self, lines, message):
        result, order_uuid = self._post_self_order(lines)
        self.assertIn('error', result, message)
        self.assertFalse(self.env['pos.order'].search([('uuid', '=', order_uuid)]),
            msg="The refused order must not be created")

    def test_valid_percent_discount_is_accepted(self):
        reward = self._create_discount_program(discount=10, discount_mode='percent').reward_ids[:1]
        result, order_uuid = self._post_self_order([
            self._product_line(self.cola, 10),
            self._discount_line(reward, -2.2),
        ])
        self.assertNotIn('error', result, result.get('error'))
        order = self.env['pos.order'].search([('uuid', '=', order_uuid)])
        reward_line = order.lines.filtered('is_reward_line')
        self.assertEqual(reward_line.tax_ids, self.default_tax15, "The discount keeps the taxes of the discounted lines")
        self.assertAlmostEqual(reward_line.price_subtotal_incl, -2.53)
        self.assertAlmostEqual(order.amount_total, 22.77)

    @mute_logger('odoo.http')
    def test_excessive_percent_discount_is_refused(self):
        reward = self._create_discount_program(discount=10, discount_mode='percent').reward_ids[:1]
        self._assert_refused([
            self._product_line(self.cola, 10),
            self._discount_line(reward, -10),
        ], "A 10% reward can't discount 46% of the order")

    @mute_logger('odoo.http')
    def test_discount_zeroing_order_is_refused(self):
        reward = self._create_discount_program(discount=10, discount_mode='percent').reward_ids[:1]
        self._assert_refused([
            self._product_line(self.cola, 10),
            self._discount_line(reward, -22),
        ], "A forged discount must not make the order free (and auto-paid)")

    @mute_logger('odoo.http')
    def test_positive_discount_is_refused(self):
        reward = self._create_discount_program(discount=10, discount_mode='percent').reward_ids[:1]
        self._assert_refused([
            self._product_line(self.cola, 10),
            self._discount_line(reward, 1),
        ], "A discount line can't increase the order total")

    @mute_logger('odoo.http')
    def test_per_order_discount_above_max_amount_is_refused(self):
        reward = self._create_discount_program(
            discount=5, discount_mode='per_order', discount_max_amount=3,
        ).reward_ids[:1]
        self._assert_refused([
            self._product_line(self.cola, 10),
            self._discount_line(reward, -4, taxes=self.env['account.tax']),
        ], "A per order discount is capped by its maximum amount")

    @mute_logger('odoo.http')
    def test_specific_discount_on_other_products_is_refused(self):
        reward = self._create_discount_program(
            discount=50, discount_mode='percent', discount_applicability='specific',
            discount_product_ids=[Command.set(self.fanta.ids)],
        ).reward_ids[:1]
        self._assert_refused([
            self._product_line(self.cola, 10),
            self._product_line(self.fanta, 1),
            # 50% of the cola lines, while the reward only applies to fanta
            self._discount_line(reward, -11),
        ], "A specific discount is bounded by the products it applies to")

    @mute_logger('odoo.http')
    def test_discount_with_foreign_tax_is_refused(self):
        other_tax = self.env['account.tax'].create({'name': 'Other Tax', 'amount': 21, 'amount_type': 'percent'})
        reward = self._create_discount_program(discount=10, discount_mode='percent').reward_ids[:1]
        self._assert_refused([
            self._product_line(self.cola, 10),
            self._discount_line(reward, -1, taxes=other_tax),
        ], "A discount can only carry taxes of the lines it discounts")

    # ------------------------------------------------------------------
    # Identification token
    # ------------------------------------------------------------------

    def _assert_identification_refused(self, result, message):
        self.assertTrue(
            result.get('error', {}).get('data', {}).get('name', '').endswith('.SelfOrderIdentificationExpired'),
            message,
        )

    def _expiration(self, token):
        return int(token.partition('.')[0])

    @mute_logger('odoo.http')
    def test_partner_without_token_is_refused(self):
        """
        Claiming to be a customer without having identified must not spend their points:
        with no card_id, _process_loyalty would otherwise pick the partner's own card.
        """
        card = self.env['loyalty.card'].create({
            'program_id': self.program.id,
            'partner_id': self.loyalty_partner.id,
            'points': 500,
        })
        result, order_uuid = self._post_self_order([self._reward_line(self.free, self.reward)], partner_token=None)
        self._assert_identification_refused(result, "A partner without identification token must be refused")
        self.assertFalse(self.env['pos.order'].search([('uuid', '=', order_uuid)]))
        card.invalidate_recordset()
        self.assertEqual(card.points, 500, "The customer's card must not have been debited")

    @mute_logger('odoo.http')
    def test_token_of_another_partner_is_refused(self):
        token = self.other_partner._get_self_order_token(self.pos_config)
        result, _order_uuid = self._post_self_order([], partner_token=token)
        self._assert_identification_refused(result, "A token only proves the identity it was issued for")

    @mute_logger('odoo.http')
    def test_token_of_another_config_is_refused(self):
        other_config = self.env['pos.config'].create({'name': 'Other Config'})
        token = self.loyalty_partner._get_self_order_token(other_config)
        result, _order_uuid = self._post_self_order([], partner_token=token)
        self._assert_identification_refused(result, "A token is only valid on the config it was issued for")

    @mute_logger('odoo.http')
    def test_expired_token_is_refused(self):
        with patch('odoo.addons.pos_self_order_loyalty.models.res_partner.time.time', return_value=time.time() - 3600):
            token = self.loyalty_partner._get_self_order_token(self.pos_config)  # kiosk: 30 minutes
        result, _order_uuid = self._post_self_order([], partner_token=token)
        self._assert_identification_refused(result, "An expired token must be refused")

    @mute_logger('odoo.http')
    def test_tampered_token_is_refused(self):
        token = self.loyalty_partner._get_self_order_token(self.pos_config)
        forged = f"{self._expiration(token) + 3600 * 24 * 365}.{token.partition('.')[2]}"
        result, _order_uuid = self._post_self_order([], partner_token=forged)
        self._assert_identification_refused(result, "Extending a token's expiration must invalidate it")

    def test_valid_token_is_accepted_and_renewed(self):
        result, order_uuid = self._post_self_order([], partner_token=VALID_TOKEN)
        self.assertNotIn('error', result, result.get('error'))
        order = self.env['pos.order'].search([('uuid', '=', order_uuid)])
        self.assertEqual(order.partner_id, self.loyalty_partner)
        partners = result['result']['res.partner']
        self.assertEqual([p['id'] for p in partners], self.loyalty_partner.ids)
        self.assertTrue(partners[0]['_self_order_token'], "The identification must slide with each order")

    @mute_logger('odoo.http')
    def test_existing_order_keeps_its_partner_without_token(self):
        cola_line = [Command.CREATE, 0, {
            "uuid": str(uuid4()), "product_id": self.cola.id, "qty": 1, "price_unit": self.cola.lst_price,
        }]
        result, order_uuid = self._post_self_order([cola_line])
        self.assertNotIn('error', result, result.get('error'))
        order = self.env['pos.order'].search([('uuid', '=', order_uuid)])

        result, _order_uuid = self._post_self_order([], partner_token=None, order_id=order.id, order_uuid=order_uuid)
        self.assertNotIn('error', result, "The partner already on the order was verified when it was set")

        result, _order_uuid = self._post_self_order(
            [], partner=self.other_partner, partner_token=None, order_id=order.id, order_uuid=order_uuid,
        )
        self._assert_identification_refused(result, "Changing the partner of an order still requires a token")
        self.assertEqual(order.partner_id, self.loyalty_partner)

    def test_validate_partner_token(self):
        """The address form proves the identity of the partner it creates, not of an existing one."""
        params = {
            'name': 'Delivery Customer', 'phone': '+32 470 00 00 00', 'street': 'Rue de la Gare 1',
            'zip': '1000', 'city': 'Brussels', 'country_id': self.env.ref('base.be').id,
        }
        created = self._jsonrpc('/pos-self-order/validate-partner', params)['result']['res.partner'][0]
        self.assertTrue(self.env['res.partner']._get_partner_from_self_order_token(
            self.pos_config, created['id'], created['_self_order_token'],
        ))
        existing = self._jsonrpc('/pos-self-order/validate-partner', {**params, 'partner_id': self.loyalty_partner.id})
        self.assertNotIn('_self_order_token', existing['result']['res.partner'][0])

    @mute_logger('odoo.http')
    def test_check_card_code_requires_token(self):
        result = self._jsonrpc('/pos-self-order/check-card-code', {
            'code': 'WHATEVER', 'partner_id': self.loyalty_partner.id, 'partner_token': None,
        })
        self._assert_identification_refused(result, "check-card-code must not trust an unproven partner")

    def test_refresh_partner_token(self):
        token = self.loyalty_partner._get_self_order_token(self.pos_config)
        result = self._jsonrpc('/pos-self-order/refresh-partner-token', {
            'partner_id': self.loyalty_partner.id, 'partner_token': token,
        })['result']
        self.assertEqual([p['id'] for p in result['res.partner']], self.loyalty_partner.ids)
        self.assertTrue(result['res.partner'][0]['_self_order_token'])

        result = self._jsonrpc('/pos-self-order/refresh-partner-token', {
            'partner_id': self.loyalty_partner.id, 'partner_token': 'invalid',
        })['result']
        self.assertEqual(result['res.partner'], [])

    def test_token_lifetime(self):
        now = time.time()
        kiosk_token = self.loyalty_partner._get_self_order_token(self.pos_config)
        self.assertAlmostEqual(self._expiration(kiosk_token) - now, 30 * 60, delta=60)
        self.pos_config.self_ordering_mode = 'mobile'
        mobile_token = self.loyalty_partner._get_self_order_token(self.pos_config)
        self.assertAlmostEqual(self._expiration(mobile_token) - now, 90 * 24 * 3600, delta=60)
