from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged, Command


@tagged('post_install', '-at_install')
class TestAnalyticAccount(AccountTestInvoicingCommon):

    def test_compute_po_count_with_different_plan(self):
        analytic_plan_1, analytic_plan_2 = self.env['account.analytic.plan'].create([
            {
                'name': 'Plan 1'
            },
            {
                'name': 'Plan 2'
            }
        ])
        analytic_account = self.env['account.analytic.account'].create({'name': 'Account', 'plan_id': analytic_plan_1.id})

        product = self.env['product.product'].create({
            'name': 'Product',
            'lst_price': 100.0,
            'standard_price': 100.0,
        })

        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'date_order': '2019-01-10',
            'order_line': [
                Command.create({
                    'product_id': product.id,
                    'product_qty': 1,
                    'analytic_distribution': {analytic_account.id: 100},
                }),
            ]
        })

        purchase_order.button_confirm()
        purchase_order.order_line.qty_received = 1

        bill = self.env['account.move'].browse(purchase_order.action_create_invoice()['res_id'])
        bill.invoice_date = '2019-01-10'

        purchase_order.invoice_ids.action_post()

        self.assertEqual(analytic_account.purchase_order_count, 1)
        analytic_account.plan_id = analytic_plan_2.id
        self.assertEqual(analytic_account.purchase_order_count, 1)
