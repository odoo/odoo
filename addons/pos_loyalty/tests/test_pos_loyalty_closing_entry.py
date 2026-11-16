# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.point_of_sale.tests.common import TestPoSCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestPosLoyaltyClosingEntry(TestPoSCommon):

    def test_reward_line_tax_tag_invert(self):
        """ A reward (discount) line is booked with the invoice repartition tags,
        so its line in the closing entry must invert them like the sale it
        discounts, even when it ends up on a separate (debit) line because the
        discounted product uses a different income account.
        """
        self.config = self.basic_config
        tax = self.taxes['tax7']
        product = self.create_product('Product', self.categ_basic, 100.0, tax_ids=tax.ids, sale_account=self.other_sale_account)
        discount_product = self.create_product('Discount', self.categ_basic, -10.0, tax_ids=tax.ids)

        self.open_new_session()
        self.env['pos.order'].sync_from_ui([self.create_ui_order_data(
            [
                {'product': product, 'quantity': 1},
                {'product': discount_product, 'quantity': 1, 'is_reward_line': True},
            ],
            payments=[(self.cash_pm1, 96.3)],
        )])
        self.pos_session.post_closing_cash_details(96.3)
        self.pos_session.close_session_from_ui()

        base_lines = self.pos_session.move_id.line_ids.filtered('tax_ids').sorted('balance')
        self.assertRecordValues(base_lines, [
            {'account_id': self.other_sale_account.id, 'balance': -100.0, 'tax_tag_ids': self.tax_tag_invoice_base.ids, 'tax_tag_invert': True},
            {'account_id': self.sale_account.id, 'balance': 10.0, 'tax_tag_ids': self.tax_tag_invoice_base.ids, 'tax_tag_invert': True},
        ])
