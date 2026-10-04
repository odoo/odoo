# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree

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

    def _assert_field_reachable_on_invoicing_user_form(self, field_name):
        # Confirm the field is genuinely reachable through the form the
        # invoicing user resolves (as the web client would), rather than
        # dead code, without letting every other field on that form leak
        # into the narrow web_read spec each test actually issues.
        view_info = self.env['sale.order'].with_user(self.invoicing_user).get_views([(False, 'form')])
        arch = etree.fromstring(view_info['views']['form']['arch'])
        field_names = {
            field.get('name')
            for field in arch.xpath('//field[not(ancestor::field) and not(ancestor::list) and not(ancestor::kanban)]')
            if field.get('name')
        }
        self.assertIn(field_name, field_names)

    def test_gift_card_count_readable_by_invoicing_user_on_draft_order(self):
        self._assert_field_reachable_on_invoicing_user_form('gift_card_count')
        # Start with a clean cache so the read below goes through the
        # invoicing user's own access rights instead of reusing a value
        # cached under another user.
        self.env.invalidate_all()
        result = self.empty_order.with_user(self.invoicing_user).web_read({'gift_card_count': {}})
        self.assertEqual(result[0]['gift_card_count'], 0)

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

        self._assert_field_reachable_on_invoicing_user_form('loyalty_data')
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
