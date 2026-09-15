from odoo import Command
from odoo.tests import tagged
from odoo.addons.project.tests.test_project_update_flow import TestProjectUpdate


@tagged('-at_install', 'post_install')
class TestProjectUpdateSaleProject(TestProjectUpdate):

    def test_project_update_profitability_values(self):
        """Ensure project updates use the correct profitability values after invoicing."""
        self.env['product.pricelist'].with_context(active_test=False).search([]).unlink()
        uom_hour = self.env.ref('uom.product_uom_hour')
        service_product = self.env['product.product'].create({
            'name': "Product service",
            'standard_price': 20,
            'list_price': 40,
            'type': 'service',
            'uom_id': uom_hour.id,
            'default_code': 'SERV-ORDERED2',
            'service_tracking': 'task_in_project',
        })

        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_1.id,
            'date_order': '2026-07-27',
            'order_line': [Command.create({
                'product_id': service_product.id,
                'product_uom_qty': 5,
            })]
        })
        sale_order.action_confirm()
        project = sale_order.project_id

        # Vendor bill
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_1.id,
            'date': '2026-07-27',
            'invoice_date': '2026-07-27',
            'invoice_line_ids': [Command.create({
                'product_id': service_product.id,
                'price_unit': 100.0,
                'analytic_distribution': {
                    f'{project.account_id.id}': 100,
                },
            })]
        })

        # Before invoicing, the full amount should remain to invoice.
        profitability_values, _ = project._get_profitability_values()
        self.assertEqual(profitability_values['to_bill_to_invoice'], 100)
        self.assertEqual(profitability_values['billed_invoiced'], 0)

        sale_order._create_invoices()
        invoice = sale_order.invoice_ids[0]
        invoice.action_post()
        bill.action_post()

        # After invoicing, the amount should move from "to invoice" to "invoiced".
        profitability_values, _ = project._get_profitability_values()
        self.assertEqual(profitability_values['to_bill_to_invoice'], 0)
        self.assertEqual(profitability_values['billed_invoiced'], 100)
