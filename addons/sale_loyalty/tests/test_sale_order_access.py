# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from odoo.addons.sale_loyalty.tests.common import TestSaleCouponCommon


@tagged('post_install', '-at_install')
class TestSaleOrderInvoicingUserAccess(TestSaleCouponCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.invoicing_user = new_test_user(
            cls.env,
            login='test_invoicing_only_user',
            groups='base.group_user,account.group_account_invoice',
            name='Invoicing Only User',
        )

    def _order_with_gift_cards(self, quantity=2):
        order = self.empty_order
        order.write({
            'order_line': [
                Command.create({
                    'product_id': self.product_gift_card.id,
                    'product_uom_qty': quantity,
                }),
            ],
        })
        order._update_programs_and_rewards()
        self.assertEqual(len(order._get_reward_coupons()), quantity)
        return order

    def test_gift_card_count_readable_by_invoicing_user_on_draft_order(self):
        order = self._order_with_gift_cards(quantity=2)
        # Start with a clean cache so the read below goes through the
        # invoicing user's own access rights instead of reusing a value
        # cached under another user.
        self.env.invalidate_all()
        result = order.with_user(self.invoicing_user).web_read({'gift_card_count': {}})
        self.assertEqual(result[0]['gift_card_count'], 2)

    def test_gift_cards_openable_by_invoicing_user(self):
        order = self._order_with_gift_cards(quantity=2)
        self.env.invalidate_all()
        action = order.with_user(self.invoicing_user).action_view_gift_cards()
        cards = self.env[action['res_model']].with_user(self.invoicing_user)
        # The list and the form of the opened cards, read as the web client
        # does, must not raise an access error.
        result = cards.web_search_read(
            action['domain'],
            {'code': {}, 'points_display': {}, 'program_id': {'fields': {'display_name': {}}}},
        )
        self.assertEqual(result['length'], 2)
        card = cards.search(action['domain'], limit=1)
        card_data = card.web_read({
            'code': {},
            'points_display': {},
            'history_ids': {'fields': {'description': {}, 'issued': {}, 'used': {}}},
        })
        self.assertEqual(card_data[0]['code'], card.code)

    def test_invoicing_user_can_only_read_loyalty_records(self):
        # Reading is what opening the gift cards of an order needs: the card,
        # its program (points display) and its history (form).
        for model in ('loyalty.card', 'loyalty.program', 'loyalty.history'):
            records = self.env[model].with_user(self.invoicing_user)
            with self.subTest(model=model):
                self.assertTrue(records.has_access('read'))
                for operation in ('write', 'create', 'unlink'):
                    self.assertFalse(records.has_access(operation), operation)

    def test_user_without_loyalty_access_reads_order_without_error(self):
        # An accounting reader can read sale.order but has no loyalty access
        # at all: the order must still open, with no gift card count.
        accounting_reader = new_test_user(
            self.env,
            login='test_accounting_readonly_user',
            groups='base.group_user,account.group_account_readonly',
            name='Accounting Read-only User',
        )
        order = self._order_with_gift_cards(quantity=2)
        order.action_confirm()
        self.env.invalidate_all()
        result = order.with_user(accounting_reader).web_read({'gift_card_count': {}, 'loyalty_data': {}})
        self.assertEqual(result[0]['gift_card_count'], 0)
        self.assertTrue(result[0]['loyalty_data'])

    def test_loyalty_data_readable_by_invoicing_user_on_confirmed_order(self):
        order = self.empty_order
        order.write({
            'order_line': [
                Command.create({
                    'product_id': self.product_A.id,
                    'name': 'Ordinary Product A',
                    'product_uom_qty': 1.0,
                }),
            ],
        })
        order._update_programs_and_rewards()
        self._auto_rewards(order, self.immediate_promotion_program)
        order.action_confirm()

        # action_confirm() above ran as the admin test user and already
        # populated the cache for order.coupon_point_ids.coupon_id, which
        # would let the invoicing user's read below reuse that cached value
        # instead of genuinely exercising its own access rights. Start with
        # a clean cache so the read is forced to go back to the database.
        self.env.invalidate_all()
        result = order.with_user(self.invoicing_user).web_read({'loyalty_data': {}})

        loyalty_data = result[0]['loyalty_data']
        self.assertTrue(loyalty_data)
        self.assertIn('point_name', loyalty_data)
        self.assertIn('issued', loyalty_data)
        self.assertIn('cost', loyalty_data)
