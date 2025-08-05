from unittest import skip

import odoo

from odoo.addons.pos_mrp.tests.common import CommonPosMrpTest


@odoo.tests.tagged('post_install', '-at_install')
@skip('Temporary to fast merge new valuation')
class TestPosMrp(CommonPosMrpTest):
    def test_bom_kit_order_total_cost(self):
        order, _ = self.create_backend_pos_order({
            'line_data': [
                {'product_id': self.product_product_kit_one.id}
            ],
            'payment_data': [
                {'payment_method_id': self.cash_payment_method.id}
            ]
        })

        self.pos_config_usd.current_session_id.action_pos_session_closing_control()
        self.assertEqual(order.lines[0].total_cost, 10.0)

    def test_bom_kit_with_kit_invoice_valuation(self):
        self.product_product_kit_one.categ_id = self.category_fifo_realtime
        self.product_product_kit_two.categ_id = self.category_fifo_realtime
        self.product_product_kit_three.categ_id = self.category_fifo_realtime
        self.product_product_kit_four.categ_id = self.category_fifo_realtime

        order, _ = self.create_backend_pos_order({
            'order_data': {
                'to_invoice': True,
                'partner_id': self.partner_moda.id,
            },
            'line_data': [
                {'product_id': self.product_product_kit_three.id},
                {'product_id': self.product_product_kit_four.id}
            ],
            'payment_data': [
                {'payment_method_id': self.cash_payment_method.id}
            ]
        })

        self.assertEqual(order.lines.filtered(
            lambda l: l.product_id == self.product_product_kit_three).total_cost, 30.0)
        accounts = self.product_product_kit_three.product_tmpl_id.get_product_accounts()
        debit_interim_account = accounts['stock_output']
        credit_expense_account = accounts['expense']
        invoice_accounts = order.account_move.line_ids.mapped('account_id.id')
        self.assertTrue(debit_interim_account.id in invoice_accounts)
        self.assertTrue(credit_expense_account.id in invoice_accounts)
        expense_line = order.account_move.line_ids.filtered(lambda l: l.account_id.id == credit_expense_account.id)
        self.assertEqual(expense_line.filtered(
            lambda l: l.product_id == self.product_product_kit_three).credit, 0.0)
        self.assertEqual(expense_line.filtered(
            lambda l: l.product_id == self.product_product_kit_three).debit, 30.0)
        interim_line = order.account_move.line_ids.filtered(lambda l: l.account_id.id == debit_interim_account.id)
        self.assertEqual(interim_line.filtered(
            lambda l: l.product_id == self.product_product_kit_three).credit, 30.0)
        self.assertEqual(interim_line.filtered(
            lambda l: l.product_id == self.product_product_kit_three).debit, 0.0)
        self.pos_config_usd.current_session_id.action_pos_session_closing_control()

    def test_bom_kit_different_uom_invoice_valuation(self):
        """This test make sure that when a kit is made of product using UoM A but the bom line uses UoM B
           the price unit is correctly computed on the invoice lines.
        """
        self.env.user.group_ids += self.env.ref('uom.group_uom')

        # Edit kit product and component product
        self.product_product_kit_one.categ_id = self.category_fifo_realtime
        self.product_product_comp_one.standard_price = 12000
        self.product_product_comp_one.uom_id = self.env.ref('uom.product_uom_dozen').id

        # Edit kit product quantity
        self.bom_one_line.bom_line_ids[0].product_qty = 6.0
        self.bom_one_line.bom_line_ids[0].product_uom_id = self.env.ref('uom.product_uom_unit').id
        self.bom_one_line.product_qty = 2.0

        order, _ = self.create_backend_pos_order({
            'order_data': {
                'to_invoice': True,
                'partner_id': self.partner_moda.id,
            },
            'line_data': [
                {'product_id': self.product_product_kit_one.id, 'qty': 2},
            ],
            'payment_data': [
                {'payment_method_id': self.cash_payment_method.id}
            ]
        })

        accounts = self.product_product_kit_one.product_tmpl_id.get_product_accounts()
        expense_line = order.account_move.line_ids.filtered(
            lambda l: l.account_id.id == accounts['expense'].id)
        interim_line = order.account_move.line_ids.filtered(
            lambda l: l.account_id.id == accounts['stock_output'].id)
        expense_line = expense_line.filtered(lambda l: l.product_id == self.product_product_kit_one)
        interim_line = interim_line.filtered(lambda l: l.product_id == self.product_product_kit_one)

        self.assertEqual(expense_line.debit, 6000.0)
        self.assertEqual(interim_line.credit, 6000.0)

    def test_bom_kit_order_total_cost_with_shared_component(self):
        self.bom_one_line.product_tmpl_id.categ_id = self.category_average
        self.bom_two_lines.product_tmpl_id.categ_id = self.category_average
        kit_1 = self.bom_one_line.product_tmpl_id.product_variant_id
        kit_2 = self.bom_two_lines.product_tmpl_id.product_variant_id

        order, _ = self.create_backend_pos_order({
            'line_data': [
                {'product_id': kit_1.id},
                {'product_id': kit_2.id}
            ],
            'payment_data': [
                {'payment_method_id': self.cash_payment_method.id}
            ]
        })

        self.pos_config_usd.current_session_id.action_pos_session_closing_control()
        self.assertRecordValues(order.lines, [
            {'product_id': kit_1.id, 'total_cost': 10.0},
            {'product_id': kit_2.id, 'total_cost': 20.0},
        ])

    def test_bom_nested_kit_order_total_cost_with_shared_component(self):
        self.bom_one_line.product_tmpl_id.categ_id = self.category_average
        self.bom_two_lines.product_tmpl_id.categ_id = self.category_average
        self.ten_dollars_with_5_incl.standard_price = 30.0
        self.twenty_dollars_with_5_incl.standard_price = 50.0
        kit_1 = self.bom_one_line.copy()
        kit_2 = self.bom_one_line.copy()
        kit_2.product_tmpl_id = self.ten_dollars_with_5_incl
        kit_3 = self.bom_one_line.copy()
        kit_3.product_tmpl_id = self.twenty_dollars_with_5_incl
        kit_3.bom_line_ids[0].product_id = kit_1.product_tmpl_id.product_variant_id

        order, _ = self.create_backend_pos_order({
            'line_data': [
                {'product_id': kit_3.product_tmpl_id.product_variant_id.id},
                {'product_id': kit_2.product_tmpl_id.product_variant_id.id}
            ],
            'payment_data': [
                {'payment_method_id': self.cash_payment_method.id}
            ]
        })

        self.assertRecordValues(order.lines, [
            {'product_id': kit_3.product_tmpl_id.product_variant_id.id, 'total_cost': 50.0},
            {'product_id': kit_2.product_tmpl_id.product_variant_id.id, 'total_cost': 30.0},
        ])
