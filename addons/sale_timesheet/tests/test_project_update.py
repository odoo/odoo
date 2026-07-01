# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from freezegun import freeze_time

from odoo import Command
from odoo.tests import tagged
from odoo.tools import format_amount
from odoo.addons.project.tests.test_project_update_flow import TestProjectUpdate

@tagged('-at_install', 'post_install')
class TestProjectUpdateSaleTimesheet(TestProjectUpdate):

    def test_project_update_description_profitability(self):
        self.project_pigs.allow_billable = True
        template_values = self.env['project.update']._get_template_values(self.project_pigs)

        # Store the formatted amount in the same currency as the project to guarantee the same unit
        comparison_amount = format_amount(self.env, 0.0, self.project_pigs.currency_id)

        self.assertEqual(template_values['profitability']['total']['costs'], 0.0, "Project costs used in the template should be well defined")
        self.assertEqual(template_values['profitability']['total']['revenues'], 0.0, "Project revenues used in the template should be well defined")
        self.assertEqual(template_values['profitability']['total']['margin'], 0, "Margin used in the template should be well defined")
        self.assertEqual(template_values['profitability']['total']['margin_percentage'], "0", "Margin percentage used in the template should be well defined")

    def test_project_update_panel_profitability_no_billable(self):
        try:
            self.project_pigs.action_view_timesheet()
        except Exception as e:
            raise AssertionError("Error raised unexpectedly while calling the action defined in profitalities action panel data ! Exception : " + e.args[0])

        try:
            self.project_pigs.action_view_timesheet()
        except Exception as e:
            raise AssertionError("Error raised unexpectedly while calling the action defined in profitalities action panel data ! Exception : " + e.args[0])

    def test_project_update_profitability_values(self):
        """Ensure project updates use the correct profitability values after invoicing."""
        uom_hour = self.env.ref('uom.product_uom_hour')
        project = self.env['project.project'].create({
            'name': 'Project',
            'allow_timesheets': True,
            'partner_id': self.partner_1.id,
            'allow_billable': True,
        })
        service_product = self.env['product.product'].create({
            'name': "Product service",
            'standard_price': 20,
            'list_price': 40,
            'type': 'service',
            'uom_id': uom_hour.id,
            'uom_po_id': uom_hour.id,
            'default_code': 'SERV-ORDERED2',
            'service_tracking': 'task_global_project',
            'project_id': project.id,
        })

        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_1.id,
            'order_line': [Command.create({
                'product_id': service_product.id,
                'product_uom_qty': 5,
            })]
        })
        sale_order.action_confirm()

        # Before invoicing, the full amount should remain to invoice.
        profitability_values = self.env['project.update']._get_profitability_values(project)
        self.assertEqual(profitability_values['to_bill_to_invoice'], 200)
        self.assertEqual(profitability_values['billed_invoiced'], 0)

        sale_order._create_invoices()
        invoice = sale_order.invoice_ids[0]
        invoice.action_post()

        # After invoicing, the amount should move from "to invoice" to "invoiced".
        profitability_values = self.env['project.update']._get_profitability_values(project)
        self.assertEqual(profitability_values['to_bill_to_invoice'], 0)
        self.assertEqual(profitability_values['billed_invoiced'], 200)
