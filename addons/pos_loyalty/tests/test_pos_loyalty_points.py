# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


@tagged('post_install', '-at_install')
class TestPOSLoyaltyPoints(TestPointOfSaleHttpCommon):
    """
    Server-side points computation: the backend recomputes points from the order lines
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'Loyalty Partner'})
        cls.whiteboard_pen_product = cls.whiteboard_pen.product_variant_id
        cls.main_pos_config.open_ui()
        cls.session = cls.main_pos_config.current_session_id

    def _create_order(self, lines, **kwargs):
        order = self.env['pos.order'].create({
            'config_id': self.main_pos_config.id,
            'session_id': self.session.id,
            'partner_id': self.partner.id,
            'lines': [Command.create(line) for line in lines],
            'amount_paid': 0,
            'amount_return': 0,
            'amount_tax': 0,
            'amount_total': 0,
            **kwargs,
        })
        order._process_loyalty()
        return order

    def _create_loyalty_program(self, rule_vals=None, reward_vals=None, **kwargs):
        return self.env['loyalty.program'].create({
            'name': 'Test Loyalty',
            'program_type': 'loyalty',
            'trigger': 'auto',
            'applies_on': 'both',
            'rule_ids': [Command.create(rule_vals or {
                'reward_point_amount': 1,
                'reward_point_mode': 'money',
                'minimum_qty': 1,
            })],
            'reward_ids': [Command.create(reward_vals or {
                'reward_type': 'discount',
                'discount_mode': 'percent',
                'discount': 10,
                'discount_applicability': 'order',
                'required_points': 5,
            })],
            **kwargs,
        })

    def _line(self, product, qty, price, **kwargs):
        return {
            'product_id': product.id,
            'qty': qty,
            'price_unit': price,
            'price_subtotal': qty * price,
            'price_subtotal_incl': qty * price,
            **kwargs,
        }

    def test_with_code_rule_earns_only_when_code_applied(self):
        """
        A with_code rule generates points only when its code was activated on the order.
        """
        program = self._create_loyalty_program(
            rule_vals={
                'mode': 'with_code',
                'code': 'PROMO10',
                'reward_point_amount': 10,
                'reward_point_mode': 'order',
                'minimum_qty': 1,
            },
            trigger='with_code',
        )
        card = self.env['loyalty.card'].create({
            'program_id': program.id,
            'partner_id': self.partner.id,
        })

        order_no_code = self._create_order([self._line(self.whiteboard_pen_product, 1, 100)])
        self.assertFalse(
            card.history_ids.filtered(lambda h: h.order_id == order_no_code.id),
            "No points should be issued without the promo code",
        )
        self.assertEqual(card.points, 0.0)

        order_with_code = self._create_order(
            [self._line(self.whiteboard_pen_product, 1, 100)], applied_codes=['PROMO10'],
        )
        card.invalidate_recordset()
        history = card.history_ids.filtered(lambda h: h.order_id == order_with_code.id)
        self.assertEqual(sum(history.mapped('issued')), 10.0, "The with_code rule should earn its points once the code is applied")
        self.assertEqual(card.points, 10.0)

    def test_points_cost_recomputed_not_trusted(self):
        """
        The client-sent points_cost is only a hint: the backend recomputes the cost
        of a claimed discount reward from the reward data.
        """
        program = self._create_loyalty_program()  # percent discount, required_points 5
        card = self.env['loyalty.card'].create({
            'program_id': program.id,
            'partner_id': self.partner.id,
        })
        card._adjust_points(50, "Initial balance")
        reward = program.reward_ids[:1]
        reward_line = self._line(
            reward.discount_line_product_id, 1, -10,
            is_reward_line=True, reward_id=reward.id, card_id=card.id,
            points_cost=1,
        )
        order = self._create_order([self._line(self.whiteboard_pen_product, 1, 100), reward_line])

        card.invalidate_recordset()
        history = card.history_ids.filtered(lambda h: h.order_id == order.id)
        self.assertEqual(sum(history.mapped('used')), 5.0, "The cost must be recomputed from the reward, not the client-sent points_cost")
        self.assertEqual(order.lines.filtered('is_reward_line').points_cost, 5.0)
        # 50 preloaded + 100 earned on the $100 line - 5 spent
        self.assertEqual(card.points, 145.0)

    def test_free_product_cost_depends_on_qty(self):
        """Free product rewards cost ceil(qty / reward_product_qty) * required_points."""
        program = self._create_loyalty_program(reward_vals={
            'reward_type': 'product',
            'reward_product_id': self.whiteboard_pen_product.id,
            'reward_product_qty': 2,
            'required_points': 3,
        })
        card = self.env['loyalty.card'].create({
            'program_id': program.id,
            'partner_id': self.partner.id,
        })
        card._adjust_points(50, "Initial balance")
        reward = program.reward_ids[:1]
        reward_line = self._line(
            self.whiteboard_pen_product, 5, 0,
            is_reward_line=True, reward_id=reward.id, card_id=card.id, points_cost=1,
        )
        order = self._create_order([reward_line])

        card.invalidate_recordset()
        history = card.history_ids.filtered(lambda h: h.order_id == order.id)
        # ceil(5 / 2) * 3 = 9 points
        self.assertEqual(sum(history.mapped('used')), 9.0)
        self.assertEqual(card.points, 41.0)

    def test_insufficient_balance_raises(self):
        """Claiming a reward the card cannot cover must fail the order processing."""
        program = self._create_loyalty_program()  # required_points 5
        card = self.env['loyalty.card'].create({
            'program_id': program.id,
            'partner_id': self.partner.id,
        })
        card._adjust_points(3, "Initial balance")
        reward = program.reward_ids[:1]
        reward_line = self._line(
            reward.discount_line_product_id, 1, -10,
            is_reward_line=True, reward_id=reward.id, card_id=card.id, points_cost=5,
        )
        with self.assertRaises(UserError):
            # 3 preloaded + 1 earned on the $1 line = 4 < 5 required
            self._create_order([self._line(self.whiteboard_pen_product, 1, 1), reward_line])

    def test_refund_prorates_earned_points(self):
        """
        A refund reverses what the origin order earned, in proportion to the
        refunded amount.
        """
        program = self._create_loyalty_program()  # 1 pt per $ spent
        origin_order = self._create_order([self._line(self.whiteboard_pen_product, 2, 50)])
        card = self.env['loyalty.card'].search([
            ('program_id', '=', program.id), ('partner_id', '=', self.partner.id),
        ])
        self.assertEqual(card.points, 100.0)

        refund_order = self._create_order(
            [self._line(
                self.whiteboard_pen_product, -1, 50,
                refunded_orderline_id=origin_order.lines[:1].id,
            )],
            is_refund=True,
        )

        card.invalidate_recordset()
        history = card.history_ids.filtered(lambda h: h.order_id == refund_order.id)
        self.assertEqual(sum(history.mapped('used')), 50.0, "Refunding half the order should reverse half the points")
        self.assertEqual(card.points, 50.0)

    def test_gift_card_refund_reverses_balance(self):
        """
        Refunding a gift-card sale must debit the card by what the origin topup
        credited it. The refund line carries no card_id (POS refund lines don't copy
        it): the card is found through the origin line.
        """
        self.env.ref('loyalty.gift_card_product_50').write({'active': True})
        gift_card_program = self.env['loyalty.program'].browse(
            self.env['loyalty.program'].create_from_template('gift_card')['res_id']
        )
        gift_card_product = self.env.ref('loyalty.gift_card_product_50')
        card = self.env['loyalty.card'].create({
            'program_id': gift_card_program.id,
            'code': 'GC-REFUND-1',
        })

        origin_order = self._create_order([
            self._line(gift_card_product, 1, 50, card_id=card.id),
        ])
        card.invalidate_recordset()
        self.assertEqual(card.points, 50.0)

        refund_order = self._create_order(
            [self._line(
                gift_card_product, -1, 50,
                refunded_orderline_id=origin_order.lines[:1].id,
            )],
            is_refund=True,
        )

        card.invalidate_recordset()
        history = card.history_ids.filtered(lambda h: h.order_id == refund_order.id)
        self.assertEqual(sum(history.mapped('used')), 50.0, "Refunding the gift card sale should debit the card")
        self.assertEqual(card.points, 0.0)

    def _earn_and_spend_program(self, points_per_unit):
        """Loyalty program that earns ``points_per_unit`` per whiteboard pen and whose
        discount reward costs a flat 150 points."""
        return self._create_loyalty_program(
            rule_vals={
                'product_ids': [Command.set(self.whiteboard_pen_product.ids)],
                'reward_point_mode': 'unit',
                'reward_point_amount': points_per_unit,
                'minimum_qty': 1,
            },
            reward_vals={
                'reward_type': 'discount',
                'discount_mode': 'percent',
                'discount': 10,
                'discount_applicability': 'order',
                'required_points': 150,
            },
        )

    def test_refund_reverses_earned_and_returns_spent(self):
        """A full refund of an order that both earned and spent points removes the
        earned points and returns the spent points."""
        program = self._earn_and_spend_program(70)
        card = self.env['loyalty.card'].create({
            'program_id': program.id,
            'partner_id': self.partner.id,
        })
        card._adjust_points(200, "Initial balance")
        reward = program.reward_ids[:1]
        reward_line = self._line(
            reward.discount_line_product_id, 1, -10,
            is_reward_line=True, reward_id=reward.id, card_id=card.id, points_cost=150,
        )
        origin_order = self._create_order([self._line(self.whiteboard_pen_product, 1, 100), reward_line])

        card.invalidate_recordset()
        origin_history = card.history_ids.filtered(lambda h: h.order_id == origin_order.id)
        self.assertEqual(sum(origin_history.mapped('issued')), 70.0)
        self.assertEqual(sum(origin_history.mapped('used')), 150.0)
        # 200 preloaded + 70 earned - 150 spent
        self.assertEqual(card.points, 120.0)

        product_line = origin_order.lines.filtered(lambda l: not l.is_reward_line)
        refund_order = self._create_order(
            [self._line(
                self.whiteboard_pen_product, -1, 100,
                refunded_orderline_id=product_line.id,
            )],
            is_refund=True,
        )

        card.invalidate_recordset()
        refund_history = card.history_ids.filtered(lambda h: h.order_id == refund_order.id)
        self.assertEqual(sum(refund_history.mapped('used')), 70.0, "The earned points must be removed")
        self.assertEqual(sum(refund_history.mapped('issued')), 150.0, "The spent points must be returned")
        self.assertEqual(card.points, 200.0, "A full refund restores the pre-order balance")

    def test_refund_prorates_earned_and_spent(self):
        """A partial refund reverses earned and spent points in proportion to the
        refunded amount."""
        program = self._earn_and_spend_program(35)
        card = self.env['loyalty.card'].create({
            'program_id': program.id,
            'partner_id': self.partner.id,
        })
        card._adjust_points(200, "Initial balance")
        reward = program.reward_ids[:1]
        reward_line = self._line(
            reward.discount_line_product_id, 1, -10,
            is_reward_line=True, reward_id=reward.id, card_id=card.id, points_cost=150,
        )
        origin_order = self._create_order([self._line(self.whiteboard_pen_product, 2, 50), reward_line])

        card.invalidate_recordset()
        # 200 preloaded + 2 * 35 earned - 150 spent
        self.assertEqual(card.points, 120.0)

        product_line = origin_order.lines.filtered(lambda l: not l.is_reward_line)
        refund_order = self._create_order(
            [self._line(
                self.whiteboard_pen_product, -1, 50,
                refunded_orderline_id=product_line.id,
            )],
            is_refund=True,
        )

        card.invalidate_recordset()
        refund_history = card.history_ids.filtered(lambda h: h.order_id == refund_order.id)
        # Half the order refunded: reverse half of both earned (70) and spent (150).
        self.assertEqual(sum(refund_history.mapped('used')), 35.0)
        self.assertEqual(sum(refund_history.mapped('issued')), 75.0)
        self.assertEqual(card.points, 160.0)
