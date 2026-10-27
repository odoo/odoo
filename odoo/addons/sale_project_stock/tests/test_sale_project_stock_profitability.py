# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, fields
from odoo.addons.sale_project.tests.test_project_profitability import TestProjectProfitabilityCommon


class TestSaleProjectStockProfitability(TestProjectProfitabilityCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        project_template = cls.env['project.project'].create({
            'name': 'sale_project_stock project template',
            'analytic_account_id': cls.analytic_account.id,
        })
        avco_real_time_product_category = cls.env['product.category'].create({
            'name': 'avco real time',
            'property_valuation': 'real_time',
            'property_cost_method': 'average',
        })
        cls.cogs_account = cls.env['account.account'].search([
            ('name', '=', 'Cost of Goods Sold'),
            ('company_id', '=', cls.env.company.id),
        ])
        cls.avco_product = cls.env['product.product'].create({
            'name': 'avco product',
            'type': 'product',
            'categ_id': avco_real_time_product_category.id,
            'standard_price': 12.0,
            'list_price': 24.0,
        })
        cls.product_superb_service = cls.env['product.product'].create({
            'name': 'product that creates project on order',
            'type': 'service',
            'standard_price': 10.0,
            'list_price': 20.0,
            'service_tracking': 'project_only',
            'project_template_id': project_template.id,
        })

    def test_report_invoice_items_anglo_saxon_automatic_valuation(self):
        """ An invoice can have some lines which should be classified/displayed under the 'Costs'
        section of a project's profitability report (specifically, COGS lines).
        """
        self.env.company.anglo_saxon_accounting = True
        self.avco_product.categ_id.property_account_expense_categ_id = self.cogs_account.id
        service_product = self.product_superb_service
        avco_product = self.avco_product
        other_avco_product = self.env['product.product'].create({
            'name': 'other avco product',
            'type': 'product',
            'categ_id': avco_product.categ_id.id,
            'standard_price': 16.0,
            'list_price': 32.0,
        })
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [Command.create({
                'product_id': service_product.id,
                'product_uom_qty': 10,
            }), Command.create({
                'product_id': avco_product.id,
                'product_uom_qty': 10,
            }), Command.create({
                'product_id': other_avco_product.id,
                'product_uom_qty': 10,
            })],
        })
        sale_order.action_confirm()
        delivery = sale_order.picking_ids
        delivery.move_ids.quantity = 10
        delivery.button_validate()
        sale_order._create_invoices()
        invoice = sale_order.invoice_ids[0]
        invoice.invoice_date = fields.Date.today()
        invoice.action_post()
        panel_data = sale_order.project_ids.get_panel_data()
        self.assertEqual(
            panel_data['profitability_items']['costs'],
            {
                'data': [{
                    'action': {
                        'args': f'["cost_of_goods_sold", [["id", "in", [{invoice.id}]]], {invoice.id}]',
                        'name': 'action_profitability_items',
                        'type': 'object',
                    },
                    'id': 'cost_of_goods_sold',
                    'billed': -280.0,
                    'sequence': 21,
                    'to_bill': 0.0,
                }],
                'total': {
                    'billed': -280.0,
                    'to_bill': 0.0,
                }
            }
        )
