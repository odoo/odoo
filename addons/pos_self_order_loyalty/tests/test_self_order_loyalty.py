# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

import odoo.tests
from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest
from odoo import fields
from odoo.fields import Command
from odoo.tools import mute_logger
from odoo.addons.mail.tests.common import MailCase


@odoo.tests.tagged("post_install", "-at_install")
class TestSelfOrderLoyalty(MailCase, SelfOrderCommonTest):
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

    def _signed(self, partner, config=None):
        """The partner id as the server signs it for a self-order client (see pos_self_order)."""
        return self.env['pos.order']._get_signed_self_partner_id(config or self.pos_config, partner.id)

    def _post_self_order(self, lines, partner=None, order_id=None, order_uuid=None, applied_codes=None, order_values=None):
        """Send a raw order payload on the public self-order endpoint.

        By default the order is made for `loyalty_partner`, with its signed id, as the genuine
        frontend does once the customer identified.
        """
        partner = self.loyalty_partner if partner is None else partner
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
            "partner_id": self._signed(partner) if partner else False,
            "lines": lines,
        }
        if applied_codes is not None:
            order["applied_codes"] = applied_codes
        order.update(order_values or {})
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
        cover the reward's point cost (see _check_self_order_loyalty_points).
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
    # Identification: the partner id signed by pos_self_order
    # ------------------------------------------------------------------
    # pos_self_order only trusts a partner_id the server signed ("<id>-<hmac>", see
    # pos.order._get_signed_self_partner_id) and drops any other from the order.

    def _create_loyalty_card(self, partner, points=500, program=None):
        return self.env['loyalty.card'].create({
            'program_id': (program or self.program).id,
            'partner_id': partner.id,
            'points': points,
        })

    @mute_logger('odoo.http')
    def test_unverified_partner_cannot_claim_a_loyalty_reward(self):
        """
        A reward of a program reserved to customers needs a verified partner: without one,
        _process_loyalty finds no card to charge and the reward would be free.
        """
        card = self._create_loyalty_card(self.loyalty_partner)
        other_config = self.env['pos.config'].create({'name': 'Other Config'})
        for partner_id in (
            False,
            self.loyalty_partner.id,  # unsigned
            f"{self.loyalty_partner.id}-forged",
            self._signed(self.loyalty_partner, other_config),
        ):
            with self.subTest(partner_id=partner_id):
                result, order_uuid = self._post_self_order(
                    [self._reward_line(self.free, self.reward)], order_values={'partner_id': partner_id},
                )
                self.assertIn('error', result, "The reward would never be charged")
                self.assertFalse(self.env['pos.order'].search([('uuid', '=', order_uuid)]))
        card.invalidate_recordset()
        self.assertEqual(card.points, 500)

    def test_signed_partner_is_kept_on_the_order(self):
        result, order_uuid = self._post_self_order([self._product_line(self.cola, 1)])
        self.assertNotIn('error', result, result.get('error'))
        self.assertEqual(self.env['pos.order'].search([('uuid', '=', order_uuid)]).partner_id, self.loyalty_partner)

    def test_identification_returns_signed_partner_and_cards(self):
        """The client must get the partner, and the cards' partner, with the id the base self-order trusts."""
        card = self._create_loyalty_card(self.loyalty_partner)
        result = self._get_partner_by_barcode()['result']
        signed = self._signed(self.loyalty_partner)
        self.assertEqual([p['id'] for p in result['res.partner']], [signed])
        self.assertEqual([(c['id'], c['partner_id']) for c in result['loyalty.card']], [(card.id, signed)])

    def test_check_card_code_only_trusts_a_signed_partner(self):
        card = self._create_loyalty_card(self.loyalty_partner)
        card.code = 'CARD-SELF-1'
        unsigned = self._jsonrpc('/pos-self-order/check-card-code', {
            'code': 'CARD-SELF-1', 'partner_id': self.loyalty_partner.id,
        })['result']
        self.assertEqual((unsigned['status'], unsigned['reason']), (False, 'invalid_partner'))
        signed = self._jsonrpc('/pos-self-order/check-card-code', {
            'code': 'CARD-SELF-1', 'partner_id': self._signed(self.loyalty_partner),
        })['result']
        self.assertTrue(signed['status'])
        self.assertEqual(signed['data']['loyalty.card'][0]['partner_id'], self._signed(self.loyalty_partner))

    def test_get_identified_partner(self):
        result = self._jsonrpc('/pos-self-order/get-identified-partner', {
            'partner_id': self._signed(self.loyalty_partner),
        })['result']
        self.assertEqual([p['id'] for p in result['res.partner']], [self._signed(self.loyalty_partner)])
        for partner_id in (self.loyalty_partner.id, f"{self.loyalty_partner.id}-forged"):
            result = self._jsonrpc('/pos-self-order/get-identified-partner', {'partner_id': partner_id})['result']
            self.assertEqual(result['res.partner'], [])

    def test_partner_from_the_delivery_form_is_kept_on_the_order(self):
        """The base delivery form returns a signed partner id: orders using it must go through."""
        partner_id = self._jsonrpc('/pos-self-order/validate-partner', {
            'name': 'Delivery Customer', 'phone': '+32 470 00 00 00', 'street': 'Rue de la Gare 1',
            'zip': '1000', 'city': 'Brussels', 'country_id': self.env.ref('base.be').id,
        })['result']['res.partner'][0]['id']
        result, order_uuid = self._post_self_order(
            [self._product_line(self.cola, 1)], order_values={'partner_id': partner_id},
        )
        self.assertNotIn('error', result, result.get('error'))
        self.assertEqual(self.env['pos.order'].search([('uuid', '=', order_uuid)]).partner_id.name, 'Delivery Customer')

    # ------------------------------------------------------------------
    # Reward lines: updates and cards
    # ------------------------------------------------------------------

    @mute_logger('odoo.http')
    def test_reward_line_update_is_checked(self):
        """An update of an existing reward line is checked as one, even if the payload doesn't say so."""
        self._create_loyalty_card(self.loyalty_partner)
        result, order_uuid = self._post_self_order([
            self._product_line(self.cola, 1),  # not free: the order stays draft and can be updated
            self._reward_line(self.free, self.reward),
        ])
        self.assertNotIn('error', result, result.get('error'))
        order = self.env['pos.order'].search([('uuid', '=', order_uuid)])
        reward_line = order.lines.filtered('is_reward_line')

        result, _order_uuid = self._post_self_order([
            [Command.UPDATE, reward_line.id, {'product_id': self.desk_organizer.id, 'qty': 1, 'price_unit': -95}],
        ], order_id=order.id, order_uuid=order_uuid)
        self.assertIn('error', result, "A reward line can't be turned into another product")
        self.assertEqual((reward_line.product_id, reward_line.price_unit), (self.free, 0))

        result, _order_uuid = self._post_self_order([
            [Command.UPDATE, reward_line.id, {'product_id': self.free.id, 'qty': 1, 'price_unit': -2.53}],
        ], order_id=order.id, order_uuid=order_uuid)
        self.assertNotIn('error', result, result.get('error'))
        self.assertEqual(reward_line.price_unit, 0, "A free product reward stays free")

    @mute_logger('odoo.http')
    def test_reward_card_of_another_program_is_refused(self):
        """A program's points can't pay for another program's rewards."""
        other_program = self.env['loyalty.program'].create({
            'name': 'Other Loyalty Program',
            'program_type': 'loyalty',
            'reward_ids': [Command.create({
                'reward_type': 'product',
                'reward_product_id': self.cola.id,
                'required_points': 1,
            })],
        })
        other_card = self._create_loyalty_card(self.loyalty_partner, program=other_program)
        result, order_uuid = self._post_self_order([self._reward_line(self.free, self.reward, other_card)])
        self.assertIn('error', result)
        self.assertFalse(self.env['pos.order'].search([('uuid', '=', order_uuid)]))
        other_card.invalidate_recordset()
        self.assertEqual(other_card.points, 500)

    def test_paid_order_stays_paid_when_points_are_missing(self):
        """
        The card was spent by another order in the meantime: once the customer paid (payment
        terminal, online), the order must still be marked paid, the shop is told instead.
        """
        card = self._create_loyalty_card(self.loyalty_partner)
        result, order_uuid = self._post_self_order([
            self._product_line(self.cola, 1),
            self._reward_line(self.free, self.reward),
        ])
        self.assertNotIn('error', result, result.get('error'))
        order = self.env['pos.order'].search([('uuid', '=', order_uuid)])
        card.points = 0  # spent elsewhere before the payment is confirmed
        self.env['pos.payment'].create({
            'pos_order_id': order.id,
            'payment_method_id': self.bank_payment_method.id,
            'amount': order.amount_total,
        })
        order.amount_paid = order.amount_total
        order.action_pos_order_paid()
        self.assertEqual(order.state, 'paid')
        self.assertIn("couldn't be processed", order.message_ids[:1].body)

    def _pay(self, order):
        self.env['pos.payment'].create({
            'pos_order_id': order.id,
            'payment_method_id': self.bank_payment_method.id,
            'amount': order.amount_total,
        })
        order.amount_paid = order.amount_total
        order.action_pos_order_paid()

    @mute_logger('odoo.http')
    def test_unaffordable_reward_is_refused_before_payment(self):
        """
        A reward the card can't afford is refused when the order is sent: once paid, the
        order can't be refused anymore (see test_paid_order_stays_paid_when_points_are_missing).
        """
        card = self._create_loyalty_card(self.loyalty_partner, points=100)
        result, order_uuid = self._post_self_order([
            self._product_line(self.cola, 1),  # not free: the order isn't paid when it's sent
            self._reward_line(self.free, self.reward, card),
        ])
        self.assertIn("enough points", result['error']['data']['message'])
        self.assertFalse(self.env['pos.order'].search([('uuid', '=', order_uuid)]))
        card.invalidate_recordset()
        self.assertEqual(card.points, 100)

    @mute_logger('odoo.http')
    def test_reward_without_card_is_checked_on_the_customer_card(self):
        """A reward line without card is charged on the customer's card of the program."""
        self._create_loyalty_card(self.loyalty_partner, points=100)
        result, order_uuid = self._post_self_order([
            self._product_line(self.cola, 1),
            self._reward_line(self.free, self.reward),
        ])
        self.assertIn('error', result)
        self.assertFalse(self.env['pos.order'].search([('uuid', '=', order_uuid)]))

    def test_points_earned_by_the_order_can_pay_its_reward(self):
        """The points the order earns count, as they do when it's paid (_process_loyalty)."""
        card = self._create_loyalty_card(self.loyalty_partner, points=199)  # + 1 for this order
        result, order_uuid = self._post_self_order([
            self._product_line(self.cola, 1),
            self._reward_line(self.free, self.reward, card),
        ])
        self.assertNotIn('error', result, result.get('error'))
        order = self.env['pos.order'].search([('uuid', '=', order_uuid)])
        card.invalidate_recordset()
        self.assertEqual(card.points, 199, "The points are only charged at payment")
        self.assertFalse(self.env['loyalty.history'].search([('order_model', '=', 'pos.order'), ('order_id', '=', order.id)]))

        self._pay(order)
        card.invalidate_recordset()
        self.assertEqual(card.points, 0)

        # Its points are spent now: sending the paid order again isn't refused for them
        result, _order_uuid = self._post_self_order([], order_id=order.id, order_uuid=order_uuid)
        self.assertNotIn('error', result, result.get('error'))

    @mute_logger('odoo.http')
    def test_gift_card_beyond_its_balance_is_refused_before_payment(self):
        card = self._create_gift_card('GIFT-SELF-1', points=10)
        gift_card_line = self._reward_line(card.program_id.reward_ids.discount_line_product_id, card.program_id.reward_ids, card)
        gift_card_line[2]['price_unit'] = -20  # the order (25.30) isn't fully paid by the card
        result, order_uuid = self._post_self_order(
            [self._product_line(self.cola, 10), gift_card_line], applied_codes=['GIFT-SELF-1'],
        )
        self.assertIn('error', result)
        self.assertFalse(self.env['pos.order'].search([('uuid', '=', order_uuid)]))
        card.invalidate_recordset()
        self.assertEqual(card.points, 10)

    # ------------------------------------------------------------------
    # Codes: the code, not a card or program id, proves a code-based reward
    # ------------------------------------------------------------------

    def _create_promo_code_program(self, code):
        return self.env['loyalty.program'].create({
            'name': 'Promo Code Program',
            'program_type': 'promo_code',
            'trigger': 'with_code',
            'applies_on': 'current',
            'rule_ids': [Command.create({
                'mode': 'with_code',
                'code': code,
                'reward_point_amount': 1,
                'reward_point_mode': 'order',
                'minimum_qty': 1,
            })],
            'reward_ids': [Command.create({
                'reward_type': 'product',
                'reward_product_id': self.cola.id,
                'reward_product_qty': 1,
                'required_points': 1,
            })],
        })

    def _create_gift_card(self, code, points):
        program = self.env['loyalty.program'].create({
            'name': 'Gift Cards',
            'program_type': 'gift_card',
            'applies_on': 'future',
            'trigger': 'auto',
            'rule_ids': [Command.create({
                'reward_point_mode': 'money',
                'reward_point_amount': 1,
                'product_ids': self.env.ref('loyalty.gift_card_product_50'),
            })],
            'reward_ids': [Command.create({
                'reward_type': 'discount',
                'discount_mode': 'per_point',
                'discount': 1,
                'discount_applicability': 'order',
                'required_points': 1,
            })],
        })
        return self.env['loyalty.card'].create({'program_id': program.id, 'code': code, 'points': points})

    def _gift_card_order_lines(self, card):
        """10 colas (25.30 tax included) fully paid by `card`: the order totals 0 and is auto-paid."""
        gift_card_line = self._reward_line(card.program_id.reward_ids.discount_line_product_id, card.program_id.reward_ids, card)
        gift_card_line[2]['price_unit'] = -25.30
        return [self._product_line(self.cola, 10), gift_card_line]

    def test_promo_code_order_with_its_code_is_accepted(self):
        """The code entered by the customer must reach the order, or a with_code rule earns nothing."""
        program = self._create_promo_code_program('PROMO-SELF')
        result, order_uuid = self._post_self_order([
            self._product_line(self.free, 1),
            self._reward_line(self.cola, program.reward_ids),
        ], applied_codes=['PROMO-SELF'])
        self.assertNotIn('error', result, result.get('error'))
        order = self.env['pos.order'].search([('uuid', '=', order_uuid)])
        self.assertEqual(order.state, 'paid')
        self.assertEqual(order.applied_codes, ['PROMO-SELF'])

    @mute_logger('odoo.http')
    def test_promo_code_reward_without_its_code_is_refused(self):
        program = self._create_promo_code_program('PROMO-SELF')
        result, order_uuid = self._post_self_order([
            self._product_line(self.free, 1),
            self._reward_line(self.cola, program.reward_ids),
        ])
        self.assertIn('error', result, "A code-activated reward can't be claimed without its code")
        self.assertFalse(self.env['pos.order'].search([('uuid', '=', order_uuid)]))

    @mute_logger('odoo.http')
    def test_anonymous_card_by_id_only_is_refused(self):
        """A gift card's id is a guessable integer: only its code proves the client holds it."""
        card = self._create_gift_card('GIFT-SELF-1', 100)
        result, order_uuid = self._post_self_order(self._gift_card_order_lines(card))
        self.assertIn('error', result, "A gift card referenced by id only must be refused")
        self.assertFalse(self.env['pos.order'].search([('uuid', '=', order_uuid)]))
        card.invalidate_recordset()
        self.assertEqual(card.points, 100, "The gift card must not have been debited")

    def test_anonymous_card_with_its_code_is_accepted(self):
        card = self._create_gift_card('GIFT-SELF-1', 100)
        result, order_uuid = self._post_self_order(self._gift_card_order_lines(card), applied_codes=['GIFT-SELF-1'])
        self.assertNotIn('error', result, result.get('error'))
        self.assertEqual(self.env['pos.order'].search([('uuid', '=', order_uuid)]).state, 'paid')
        card.invalidate_recordset()
        self.assertAlmostEqual(card.points, 74.70)

    def test_promo_codes_are_not_loaded_in_self_order(self):
        """With the public mobile access token, anyone could read the codes and apply them."""
        fields = self.env['loyalty.rule']._load_pos_self_data_fields(self.pos_config)
        self.assertNotIn('code', fields)
        self.assertNotIn('promo_barcode', fields)

    def test_entered_promo_code_is_returned(self):
        """The client needs the rule's code to apply it: only revealed to who entered it."""
        program = self._create_promo_code_program('PROMO-SELF')
        result = self._jsonrpc('/pos-self-order/check-card-code', {'code': 'PROMO-SELF'})['result']
        self.assertTrue(result['status'])
        self.assertEqual(
            [(rule['id'], rule['code']) for rule in result['data']['loyalty.rule']],
            [(program.rule_ids.id, 'PROMO-SELF')],
        )

    def test_applied_codes_are_loaded_in_self_order(self):
        """The self-order client only sends the fields it loads: applied_codes must be one of them."""
        self.assertIn('applied_codes', self.env['pos.order']._load_pos_self_data_fields(self.pos_config))

    # ------------------------------------------------------------------
    # Loyalty state (active_rewards, active_payment_programs, disabled_program_ids)
    # ------------------------------------------------------------------
    # The classic POS replays this state when it opens a self-order (recomputeRewards), with
    # none of the self-order checks: what reaches the order must be what a genuine self-order
    # client could have built.

    def _post_draft_order_with_state(self, applied_codes=None, **state):
        """A non-free order (it stays draft) carrying the given loyalty state."""
        cola_line = [Command.CREATE, 0, {
            "uuid": str(uuid4()), "product_id": self.cola.id, "qty": 1, "price_unit": self.cola.lst_price,
        }]
        result, order_uuid = self._post_self_order([cola_line], applied_codes=applied_codes, order_values=state)
        self.assertNotIn('error', result, result.get('error'))
        return self.env['pos.order'].search([('uuid', '=', order_uuid)])

    def test_loyalty_state_is_kept(self):
        """A self-order's rewards must reach the order, so a classic POS can take it over."""
        partner_card = self.env['loyalty.card'].create({
            'program_id': self.program.id,
            'partner_id': self.loyalty_partner.id,
            'points': 500,
        })
        gift_card = self._create_gift_card('GIFT-SELF-1', 100)
        state = {
            'active_rewards': [{
                'reward_id': self.reward.id,
                'qty': 1,
                'reward_product_id': self.free.id,
                'attribute_value_ids': [],
                'attribute_custom_values': {},
                'card_id': partner_card.id,
            }],
            'active_payment_programs': [{
                'reward_id': gift_card.program_id.reward_ids.id,
                'card_id': gift_card.id,
                'amount': 10,
            }],
            'disabled_program_ids': [self.program.id],
        }
        order = self._post_draft_order_with_state(applied_codes=['GIFT-SELF-1'], **state)
        self.assertEqual(order.active_rewards, state['active_rewards'])
        self.assertEqual(order.active_payment_programs, state['active_payment_programs'])
        self.assertEqual(order.disabled_program_ids, state['disabled_program_ids'])

    def test_forged_loyalty_state_is_stripped(self):
        other_config = self.env['pos.config'].create({'name': 'Other Config'})
        foreign_program = self.env['loyalty.program'].create({
            'name': 'Foreign Program',
            'program_type': 'loyalty',
            'pos_config_ids': [Command.link(other_config.id)],
            'reward_ids': [Command.create({
                'reward_type': 'product',
                'reward_product_id': self.free.id,
                'required_points': 1,
            })],
        })
        other_partner_card = self.env['loyalty.card'].create({
            'program_id': self.program.id,
            'partner_id': self.other_partner.id,
            'points': 500,
        })
        gift_card = self._create_gift_card('GIFT-SELF-1', 100)
        order = self._post_draft_order_with_state(
            active_rewards=[
                {'reward_id': foreign_program.reward_ids.id},  # program unavailable on this config
                {'reward_id': self.reward.id, 'reward_product_id': self.cola.id},  # product not granted
                {'reward_id': self.reward.id, 'card_id': other_partner_card.id},  # card of someone else
                {'reward_id': self.reward.id, 'attribute_value_ids': [999999]},  # unknown attribute
                {'reward_id': self.reward.id, 'qty': -5},  # nonsensical quantity
                'not a dict',
                {'reward_id': self.reward.id, 'injected': 'value'},  # kept, without the unknown key
            ],
            active_payment_programs=[
                {'reward_id': gift_card.program_id.reward_ids.id, 'card_id': gift_card.id},  # code not entered
                {'reward_id': self.reward.id, 'card_id': gift_card.id},  # reward of another program
            ],
            disabled_program_ids=['x', 999999, foreign_program.id, self.program.id],
        )
        self.assertEqual(order.active_rewards, [{'reward_id': self.reward.id}])
        self.assertFalse(order.active_payment_programs)  # an empty Json list is stored as NULL
        self.assertEqual(order.disabled_program_ids, [self.program.id])

    def test_loyalty_state_is_loaded_in_self_order(self):
        fields = self.env['pos.order']._load_pos_self_data_fields(self.pos_config)
        for field in ('active_rewards', 'active_payment_programs', 'disabled_program_ids'):
            self.assertIn(field, fields)

    # ------------------------------------------------------------------
    # Barcode identification: kiosk only
    # ------------------------------------------------------------------
    # A partner barcode is often short and sequential (typed by staff, see the "042" prefix
    # convention). Outside a kiosk the config access token is public (printed in the table QR
    # codes), so anyone could enumerate barcodes and get identification tokens for them.

    def _get_partner_by_barcode(self):
        self.loyalty_partner.barcode = '0420000000001'
        return self._jsonrpc('/pos-self-order/get-partner-by-barcode', {'partner_barcode': '0420000000001'})

    def test_empty_barcode_identifies_nobody(self):
        """A search on an empty barcode would match the customers who have none."""
        for barcode in (False, None, ''):
            with self.subTest(barcode=barcode):
                result = self._jsonrpc('/pos-self-order/get-partner-by-barcode', {'partner_barcode': barcode})
                self.assertEqual(result.get('result'), {})

    def test_partner_barcode_identifies_in_kiosk(self):
        result = self._get_partner_by_barcode()
        self.assertNotIn('error', result, result.get('error'))
        partners = result['result']['res.partner']
        self.assertEqual([p['id'] for p in partners], [self._signed(self.loyalty_partner)])

    @mute_logger('odoo.http')
    def test_partner_barcode_refused_outside_kiosk(self):
        for mode in ('mobile', 'consultation'):
            with self.subTest(mode=mode):
                self.pos_config.self_ordering_mode = mode
                result = self._get_partner_by_barcode()
                self.assertNotIn('result', result, "No partner data may leak outside a kiosk")
                self.assertEqual(result['error']['data']['name'], 'werkzeug.exceptions.Unauthorized')

    # ------------------------------------------------------------------
    # Email identification
    # ------------------------------------------------------------------
    # The code is pinned to 111111 (secrets.choice) to stand for the one read in the mailbox.

    def _request_code(self, mail):
        with patch('secrets.choice', return_value='1'):
            return self._jsonrpc('/pos-self-order/get-partner-by-mail', {'mail': mail})

    def _validate_code(self, mail, code):
        return self._jsonrpc('/pos-self-order/validate-partner-code', {'mail': mail, 'code': code})['result']

    def _partners_with_email(self, mail):
        return self.env['res.partner'].search([('email_normalized', '=', mail)])

    def test_email_code_request_reveals_nothing(self):
        """Same answer whether the email is a customer or not: no customer data, no token."""
        self.loyalty_partner.email = 'known@example.com'
        known = self._request_code('known@example.com')
        unknown = self._request_code('unknown@example.com')
        self.assertNotIn('error', unknown, unknown.get('error'))
        self.assertEqual(known['result'], unknown['result'], "The answer must not tell whether the email is a customer")
        self.assertNotIn('res.partner', unknown['result'])
        self.assertFalse(self._partners_with_email('unknown@example.com'), "No customer before the code is validated")

    def test_new_customer_created_once_the_code_is_validated(self):
        self._request_code('new@example.com')
        result = self._validate_code('new@example.com', '111111')
        partner = self._partners_with_email('new@example.com')
        self.assertEqual(len(partner), 1)
        self.assertEqual([p['id'] for p in result['res.partner']], [self._signed(partner)])

    def test_wrong_code_is_refused(self):
        self._request_code('new@example.com')
        self.assertEqual(self._validate_code('new@example.com', '222222')['res.partner'], [])
        self.assertFalse(self._partners_with_email('new@example.com'))

    def test_existing_customer_found_by_normalized_email(self):
        """A stored "Name <Address>" or capitals must not lead to a duplicate customer."""
        self.loyalty_partner.email = '"Alice" <Alice@Example.com>'
        self._request_code('alice@example.com')
        result = self._validate_code('alice@example.com', '111111')
        self.assertEqual([p['id'] for p in result['res.partner']], [self._signed(self.loyalty_partner)])
        self.assertEqual(self._partners_with_email('alice@example.com'), self.loyalty_partner)

    def test_code_is_single_use_and_attempts_are_limited(self):
        self._request_code('new@example.com')
        self.assertTrue(self._validate_code('new@example.com', '111111')['res.partner'])
        self.assertEqual(self._validate_code('new@example.com', '111111')['res.partner'], [], "A code is single use")

        self.env['pos_self_order_loyalty.otp'].search([]).sent_at = '2000-01-01'  # skip the resend cooldown
        self._request_code('new@example.com')
        for _attempt in range(5):
            self._validate_code('new@example.com', '222222')
        self.assertEqual(
            self._validate_code('new@example.com', '111111')['res.partner'], [],
            "Once the attempts are exhausted, even the right code is refused",
        )

    # A new code doesn't give new chances: wrong codes are counted per email over 24 hours

    def _skip_resend_cooldown(self):
        self.env['pos_self_order_loyalty.otp'].search([]).sent_at = '2000-01-01'

    def _fail_codes(self, mail, count):
        """Request a new code (once the cooldown is over), then send `count` wrong ones."""
        self._skip_resend_cooldown()
        self._request_code(mail)
        for _attempt in range(count):
            self._validate_code(mail, '222222')

    def test_wrong_codes_are_not_reset_by_new_codes(self):
        for _round in range(3):
            self._fail_codes('new@example.com', 5)  # 15 wrong codes in total
        self._skip_resend_cooldown()
        request = self._request_code('new@example.com')['result']
        self.assertEqual(request, {'code_sent': False, 'too_many_attempts': True})
        result = self._validate_code('new@example.com', '111111')
        self.assertEqual(result['res.partner'], [], "A blocked email is refused even with the right code")
        self.assertTrue(result['too_many_attempts'])

    def test_blocked_email_is_unblocked_after_24_hours(self):
        for _round in range(3):
            self._fail_codes('new@example.com', 5)
        self.env['pos_self_order_loyalty.otp'].search([]).failures_since = fields.Datetime.now() - timedelta(hours=25)
        self._skip_resend_cooldown()
        self.assertEqual(self._request_code('new@example.com')['result'], {'code_sent': True})
        self.assertTrue(self._validate_code('new@example.com', '111111')['res.partner'])

    def test_identification_resets_wrong_codes(self):
        self._fail_codes('new@example.com', 5)
        self._fail_codes('new@example.com', 5)
        self._fail_codes('new@example.com', 4)  # 14 wrong codes
        self.assertTrue(self._validate_code('new@example.com', '111111')['res.partner'])
        for _round in range(2):
            self._fail_codes('new@example.com', 5)
        self._fail_codes('new@example.com', 4)  # 14 more since the identification
        self.assertTrue(
            self._validate_code('new@example.com', '111111')['res.partner'],
            "Wrong codes from before a successful identification don't count anymore",
        )

    # ------------------------------------------------------------------
    # Delivery addresses of an identified customer
    # ------------------------------------------------------------------

    def _enable_delivery(self):
        self.pos_config.write({
            'use_presets': True,
            'available_preset_ids': [Command.set(self.delivery_preset.ids)],
            'default_preset_id': self.delivery_preset.id,
        })

    def _signed_address(self, address):
        return self.env['pos.order']._get_signed_self_address_id(self.pos_config, address.parent_id or address, address)

    def _validate_address(self, partner=None, **values):
        partner = self.loyalty_partner if partner is None else partner
        return self._jsonrpc('/pos-self-order/validate-partner', {
            'preset_id': self.delivery_preset.id,
            'partner_id': self._signed(partner),
            **values,
        })['result']

    def _address_values(self, street='Rue de la Gare 1'):
        return {
            'name': 'Loyalty Customer', 'phone': '+32 470 00 00 00', 'street': street,
            'zip': '1000', 'city': 'Brussels', 'country_id': self.env.ref('base.be').id,
        }

    def _create_delivery_address(self, partner, street='Avenue Louise 2'):
        return self.env['res.partner'].create({
            'type': 'delivery', 'parent_id': partner.id, 'name': 'Office', 'street': street,
            'phone': '+32 470 11 11 11',
        })

    def test_first_address_is_written_on_the_customer(self):
        """A customer without an address gets the one they enter, no new contact is made."""
        self.loyalty_partner.write({'name': 'customer@example.com', 'email': 'customer@example.com'})
        result = self._validate_address(**self._address_values())
        self.assertEqual([p['id'] for p in result['res.partner']], [self._signed(self.loyalty_partner)])
        self.assertRecordValues(self.loyalty_partner, [{
            'street': 'Rue de la Gare 1', 'city': 'Brussels', 'phone': '+32 470 00 00 00',
            'name': 'Loyalty Customer',  # replaces the email it was named after
        }])
        self.assertFalse(self.loyalty_partner.child_ids)

    def test_new_address_is_a_delivery_contact_of_the_customer(self):
        self.loyalty_partner.street = 'Home Street 1'
        result = self._validate_address(**self._address_values())
        address = self.loyalty_partner.child_ids
        self.assertRecordValues(address, [{'type': 'delivery', 'street': 'Rue de la Gare 1'}])
        self.assertEqual([p['id'] for p in result['res.partner']], [self._signed_address(address)])
        self.assertNotEqual(self._signed_address(address), self._signed(address),
            "A delivery address isn't signed as a proof of identity")
        self.assertEqual(self.loyalty_partner.street, 'Home Street 1')

        self._validate_address(**self._address_values())
        self.assertEqual(self.loyalty_partner.child_ids, address, "The same address is reused")

    def test_address_choice_is_checked(self):
        own_address = self._create_delivery_address(self.loyalty_partner)
        result = self._validate_address(delivery_partner_id=self._signed_address(own_address))
        self.assertEqual([p['id'] for p in result['res.partner']], [self._signed_address(own_address)])

        other_address = self._create_delivery_address(self.other_partner)
        for delivery_partner_id in (
            self._signed_address(other_address),  # someone else's
            own_address.id,  # unsigned
            f"{own_address.id}-forged",
        ):
            with self.subTest(delivery_partner_id=delivery_partner_id):
                result = self._validate_address(delivery_partner_id=delivery_partner_id)
                self.assertEqual(result['error']['type'], 'address')
        own_address.action_archive()
        result = self._validate_address(delivery_partner_id=self._signed_address(own_address))
        self.assertEqual(result['error']['type'], 'address', "An archived address can't be chosen anymore")

    def test_unidentified_customer_keeps_the_base_delivery_form(self):
        result = self._jsonrpc('/pos-self-order/validate-partner', {
            'preset_id': self.delivery_preset.id, **self._address_values(),
        })['result']
        partner = self.env['pos.order']._get_self_partner_from_token(self.pos_config, result['res.partner'][0]['id'])
        self.assertEqual(partner.street, 'Rue de la Gare 1')
        self.assertFalse(partner.parent_id)

    def test_order_is_delivered_to_the_customer_address(self):
        self._enable_delivery()
        address = self._create_delivery_address(self.loyalty_partner)
        result, order_uuid = self._post_self_order([self._product_line(self.cola, 1)], order_values={
            'preset_id': self.delivery_preset.id,
            'delivery_partner_id': self._signed_address(address),
        })
        self.assertNotIn('error', result, result.get('error'))
        order = self.env['pos.order'].search([('uuid', '=', order_uuid)])
        self.assertRecordValues(order, [{
            'partner_id': self.loyalty_partner.id,
            'delivery_partner_id': address.id,
            'mobile': '+32 470 11 11 11',
        }])
        self.assertEqual(result['result']['pos.order'][0]['delivery_partner_id'], self._signed_address(address))
        receipt_partner = order._get_common_record_data()['partner']
        self.assertEqual((receipt_partner['name'], receipt_partner['street']), ('Loyalty Customer', 'Avenue Louise 2'),
            "The receipt shows the customer with the delivery address")

        order.email = 'customer@example.com'
        with self.mock_mail_gateway():
            order.action_send_self_order_receipt(
                order.email, self.env.ref('pos_self_order.delivery_email_template').id, False, False,
            )
        self.assertEqual(len(self._new_mails), 1)
        self.assertEqual(self._new_mails.email_to, 'customer@example.com')
        self.assertIn('Avenue Louise 2', self._new_mails.body_html, "The mail shows the delivery address")

    def test_foreign_delivery_address_is_ignored(self):
        self._enable_delivery()
        other_address = self._create_delivery_address(self.other_partner)
        for delivery_partner_id in (self._signed_address(other_address), other_address.id):
            with self.subTest(delivery_partner_id=delivery_partner_id):
                result, order_uuid = self._post_self_order([self._product_line(self.cola, 1)], order_values={
                    'preset_id': self.delivery_preset.id,
                    'delivery_partner_id': delivery_partner_id,
                })
                self.assertNotIn('error', result, result.get('error'))
                self.assertFalse(self.env['pos.order'].search([('uuid', '=', order_uuid)]).delivery_partner_id)

    def test_get_delivery_addresses(self):
        self.loyalty_partner.street = 'Home Street 1'
        address = self._create_delivery_address(self.loyalty_partner)
        self._create_delivery_address(self.other_partner)
        self.env['res.partner'].create({'parent_id': self.loyalty_partner.id, 'type': 'invoice', 'street': 'Billing 1'})
        result = self._jsonrpc('/pos-self-order/get-delivery-addresses', {
            'partner_id': self._signed(self.loyalty_partner),
        })['result']
        self.assertEqual(
            [p['id'] for p in result['res.partner']],
            [self._signed(self.loyalty_partner), self._signed_address(address)],
        )
        result = self._jsonrpc('/pos-self-order/get-delivery-addresses', {
            'partner_id': self.loyalty_partner.id,
        })['result']
        self.assertEqual(result['res.partner'], [], "Only a verified customer gets their addresses")

    @mute_logger('odoo.http')
    def test_archive_delivery_address(self):
        address = self._create_delivery_address(self.loyalty_partner)
        other_address = self._create_delivery_address(self.other_partner)
        for partner, delivery_partner_id in (
            (self.loyalty_partner, self._signed(self.loyalty_partner)),  # their own contact
            (self.loyalty_partner, self._signed_address(other_address)),
            (self.other_partner, self._signed_address(address)),
        ):
            with self.subTest(partner=partner.name, delivery_partner_id=delivery_partner_id):
                result = self._jsonrpc('/pos-self-order/archive-delivery-address', {
                    'partner_id': self._signed(partner), 'delivery_partner_id': delivery_partner_id,
                })
                self.assertEqual(result['error']['data']['name'], 'werkzeug.exceptions.Forbidden')
        self.assertTrue(self.loyalty_partner.active and address.active and other_address.active)

        result = self._jsonrpc('/pos-self-order/archive-delivery-address', {
            'partner_id': self._signed(self.loyalty_partner), 'delivery_partner_id': self._signed_address(address),
        })
        self.assertTrue(result['result'])
        self.assertFalse(address.active)
