# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tools import float_is_zero, float_compare
from odoo.addons.sale_timesheet.tests.common import TestCommonSaleTimesheet


class TestCommonReporting(TestCommonSaleTimesheet):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        # expense product
        cls.product_expense = cls.env['product.product'].with_context(mail_notrack=True, mail_create_nolog=True).create({
            'name': "Expense service",
            'standard_price': 10,
            'list_price': 20,
            'type': 'service',
            'invoice_policy': 'delivery',
            'expense_policy': 'sales_price',
            'default_code': 'EXP',
            'service_type': 'manual',
            'taxes_id': False,
            'property_account_income_id': cls.company_data['default_account_revenue'].id,
        })

        # create Analytic Accounts
        cls.analytic_account_1 = cls.env['account.analytic.account'].create({
            'name': 'Test AA 1',
            'code': 'AA1',
            'company_id': cls.company_data['company'].id,
            'partner_id': cls.partner_a.id
        })
        cls.analytic_account_2 = cls.env['account.analytic.account'].create({
            'name': 'Test AA 2',
            'code': 'AA2',
            'company_id': cls.company_data['company'].id,
            'partner_id': cls.partner_a.id
        })
        cls.analytic_account_3 = cls.env['account.analytic.account'].create({
            'name': 'Test AA 3',
            'code': 'AA3',
            'company_id': cls.company_data['company'].id,
            'partner_id': cls.partner_a.id
        })

        # Sale orders each will create project and a task in a global project (one SO is 'delivered', the other is 'ordered')
        # and a third one using fixed_price (which is 'delivered')
        cls.sale_order_1 = cls.env['sale.order'].with_context(mail_notrack=True, mail_create_nolog=True).create({
            'partner_id': cls.partner_a.id,
            'partner_invoice_id': cls.partner_a.id,
            'partner_shipping_id': cls.partner_a.id,
            'analytic_account_id': cls.analytic_account_1.id,
        })
        cls.so_line_deliver_project = cls.env['sale.order.line'].create({
            'name': cls.product_delivery_timesheet3.name,
            'product_id': cls.product_delivery_timesheet3.id,
            'product_uom_qty': 5,
            'product_uom': cls.product_delivery_timesheet3.uom_id.id,
            'price_unit': cls.product_delivery_timesheet3.list_price,
            'order_id': cls.sale_order_1.id,
        })
        cls.so_line_deliver_task = cls.env['sale.order.line'].create({
            'name': cls.product_delivery_timesheet2.name,
            'product_id': cls.product_delivery_timesheet2.id,
            'product_uom_qty': 7,
            'product_uom': cls.product_delivery_timesheet2.uom_id.id,
            'price_unit': cls.product_delivery_timesheet2.list_price,
            'order_id': cls.sale_order_1.id,
        })

        cls.sale_order_2 = cls.env['sale.order'].with_context(mail_notrack=True, mail_create_nolog=True).create({
            'partner_id': cls.partner_a.id,
            'partner_invoice_id': cls.partner_a.id,
            'partner_shipping_id': cls.partner_a.id,
            'analytic_account_id': cls.analytic_account_2.id,
        })
        cls.so_line_order_project = cls.env['sale.order.line'].create({
            'name': cls.product_order_timesheet3.name,
            'product_id': cls.product_order_timesheet3.id,
            'product_uom_qty': 5,
            'product_uom': cls.product_order_timesheet3.uom_id.id,
            'price_unit': cls.product_order_timesheet3.list_price,
            'order_id': cls.sale_order_2.id,
        })
        cls.so_line_order_task = cls.env['sale.order.line'].create({
            'name': cls.product_order_timesheet2.name,
            'product_id': cls.product_order_timesheet2.id,
            'product_uom_qty': 7,
            'product_uom': cls.product_order_timesheet2.uom_id.id,
            'price_unit': cls.product_order_timesheet2.list_price,
            'order_id': cls.sale_order_2.id,
        })

        cls.sale_order_3 = cls.env['sale.order'].with_context(mail_notrack=True, mail_create_nolog=True).create({
            'partner_id': cls.partner_a.id,
            'partner_invoice_id': cls.partner_a.id,
            'partner_shipping_id': cls.partner_a.id,
            'analytic_account_id': cls.analytic_account_3.id,
        })
        cls.so_line_deliver_manual_project = cls.env['sale.order.line'].create({
            'name': cls.product_delivery_manual3.name,
            'product_id': cls.product_delivery_manual3.id,
            'product_uom_qty': 11,
            'product_uom': cls.product_delivery_manual3.uom_id.id,
            'price_unit': cls.product_delivery_manual3.list_price,
            'order_id': cls.sale_order_3.id,
        })

    def _log_timesheet_user(self, project, unit_amount, task=False):
        """ Utility method to log timesheet """
        Timesheet = self.env['account.analytic.line']
        return Timesheet.create({
            'name': 'timesheet employee on project_so_1 only',
            'account_id': project.analytic_account_id.id,
            'project_id': project.id,
            'employee_id': self.employee_user.id,
            'unit_amount': unit_amount,
            'task_id': task.id if task else False,
        })

    def _log_timesheet_manager(self, project, unit_amount, task=False):
        """ Utility method to log timesheet """
        Timesheet = self.env['account.analytic.line']
        return Timesheet.create({
            'name': 'timesheet employee on project_so_1 only',
            'account_id': project.analytic_account_id.id,
            'project_id': project.id,
            'employee_id': self.employee_manager.id,
            'unit_amount': unit_amount,
            'task_id': task.id if task else False,
        })
