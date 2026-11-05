# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.point_of_sale.tests.common import TestPoSCommon


@tagged('post_install', '-at_install')
class TestClosingEntryTaxTags(TestPoSCommon):

    def setUp(self):
        super().setUp()
        self.config = self.basic_config
        self.config.is_closing_entry_by_product = True
        self.tax_tag_refund_base.tax_negate = True
        self.product = self.create_product('Product', self.categ_basic, 100.0, tax_ids=self.taxes['tax7'].ids)
        self.reward_product = self.create_product('Reward', self.categ_basic, 0.0, tax_ids=self.taxes['tax7'].ids)

    def _get_base_grid_amount(self, moves):
        base_tags = self.tax_tag_invoice_base | self.tax_tag_refund_base
        return sum(
            line.balance
            * (-1 if tag.tax_negate else 1)
            * (-1 if line.tax_tag_invert else 1)
            for line in moves.line_ids
            for tag in line.tax_tag_ids & base_tags
        )

    def test_reward_line_reduces_base_grid(self):
        """A loyalty reward is a sales line with a debit balance on the closing entry: it must
        reduce the reported base. The reversal must cancel that contribution,
        even if its lines use refund base grids.
        """
        self.open_new_session()
        order_data = self.create_ui_order_data(
            [(self.product, 1), (self.reward_product, 1)],
            payments=[(self.cash_pm1, 96.3)],
        )
        reward_line_vals = order_data['lines'][1][2]
        reward_line_vals.update({
            'price_unit': -10.0,
            'price_subtotal': -10.0,
            'price_subtotal_incl': -10.7,
            'is_reward_line': True,
        })
        order_data.update({'amount_tax': 6.3, 'amount_total': 96.3})

        self.env['pos.order'].sync_from_ui([order_data])
        self.pos_session.action_pos_session_validate()

        closing_move = self.pos_session.move_id
        reward_line = closing_move.line_ids.filtered(lambda line: line.product_id == self.reward_product)
        self.assertRecordValues(reward_line, [{
            'balance': 10.0,
            'tax_tag_ids': self.tax_tag_invoice_base.ids,
            'tax_tag_invert': True,
        }])
        self.assertAlmostEqual(self._get_base_grid_amount(closing_move), 90.0)

        reversal_move = closing_move._reverse_moves()
        self.assertAlmostEqual(self._get_base_grid_amount(reversal_move), -90.0)
        self.assertAlmostEqual(self._get_base_grid_amount(closing_move | reversal_move), 0.0)
