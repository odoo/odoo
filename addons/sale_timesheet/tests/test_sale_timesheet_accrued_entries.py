# -*- coding: utf-8 -*-
from odoo import fields
from odoo.addons.sale_timesheet.tests.common import TestCommonSaleTimesheet
from odoo.tests import tagged
from odoo.exceptions import UserError


@tagged('post_install', '-at_install')
class TestAccruedTimeSheetSaleOrders(TestCommonSaleTimesheet):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.sale_order = cls.env['sale.order'].create({
            'partner_id': cls.partner_a.id,
            'partner_invoice_id': cls.partner_a.id,
            'partner_shipping_id': cls.partner_a.id,
            'date_order': '2020-01-01',
        })
        so_line_deliver_global_project = cls.env['sale.order.line'].create({
            'name': cls.product_delivery_timesheet2.name,
            'product_id': cls.product_delivery_timesheet2.id,
            'product_uom_qty': 50,
            'price_unit': cls.product_delivery_timesheet2.list_price,
            'order_id': cls.sale_order.id,
        })
        cls.sale_order.action_confirm()

        cls.task = cls.env['project.task'].search([('sale_line_id', '=', so_line_deliver_global_project.id)])
        cls.account_revenue = cls.company_data['default_account_revenue']

    def _log_hours(self, unit_amount, date):
        self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': self.task.project_id.id,
            'task_id': self.task.id,
            'unit_amount': unit_amount,
            'employee_id': self.employee_manager.id,
            'date': date,
        })

    def test_timesheet_accrued_entries(self):
        # log 10 hours on 2020-01-02
        self._log_hours(10, '2020-01-02')
        # log 10 hours on 2020-01-05
        self._log_hours(10, '2020-01-05')
        wizard = self.env['account.accrued.orders.wizard'].with_context({
            'active_model': 'sale.order',
            'active_ids': self.sale_order.ids,
        }).create({
            'account_id': self.company_data['default_account_expense'].id,
            'date': '2020-01-01',
        })

        # nothing to invoice on 2020-01-01
        with self.assertRaises(UserError):
            wizard.create_entries()

        # 10 hours to invoice on 2020-01-03
        wizard.date = fields.Date.to_date('2020-01-03')
        self.assertRecordValues(self.env['account.move'].search(wizard.create_entries()['domain']).line_ids, [
            # reverse move lines
            {'account_id': self.account_revenue.id, 'debit': 900, 'credit': 0},
            {'account_id': wizard.account_id.id, 'debit': 0, 'credit': 900},
            # move lines
            {'account_id': self.account_revenue.id, 'debit': 0, 'credit': 900},
            {'account_id': wizard.account_id.id, 'debit': 900, 'credit': 0},
        ])

        # 20 hours to invoice on 2020-01-07
        wizard.date = fields.Date.to_date('2020-01-07')
        self.assertRecordValues(self.env['account.move'].search(wizard.create_entries()['domain']).line_ids, [
            # reverse move lines
            {'account_id': self.account_revenue.id, 'debit': 1800, 'credit': 0},
            {'account_id': wizard.account_id.id, 'debit': 0, 'credit': 1800},
            # move lines
            {'account_id': self.account_revenue.id, 'debit': 0, 'credit': 1800},
            {'account_id': wizard.account_id.id, 'debit': 1800, 'credit': 0},
        ])

    def test_timesheet_invoiced_accrued_entries(self):
        # log 10 hours on 2020-01-02
        self._log_hours(10, '2020-01-02')

        # invoice on 2020-01-04
        inv = self.sale_order._create_invoices()
        inv.invoice_date = fields.Date.to_date('2020-01-04')
        inv.action_post()

        # log 10 hours on 2020-01-06
        self._log_hours(10, '2020-01-06')

        # invoice on 2020-01-08
        inv = self.sale_order._create_invoices()
        inv.invoice_date = fields.Date.to_date('2020-01-08')
        inv.action_post()

        wizard = self.env['account.accrued.orders.wizard'].with_context({
            'active_model': 'sale.order',
            'active_ids': self.sale_order.ids,
        }).create({
            'account_id': self.company_data['default_account_expense'].id,
            'date': '2020-01-02',
        })
        self.assertRecordValues(self.env['account.move'].search(wizard.create_entries()['domain']).line_ids, [
            # reverse move lines
            {'account_id': self.account_revenue.id, 'debit': 900, 'credit': 0},
            {'account_id': wizard.account_id.id, 'debit': 0, 'credit': 900},
            # move lines
            {'account_id': self.account_revenue.id, 'debit': 0, 'credit': 900},
            {'account_id': wizard.account_id.id, 'debit': 900, 'credit': 0},
        ])

        # nothing to invoice on 2020-01-05
        wizard.date = fields.Date.to_date('2020-01-05')
        with self.assertRaises(UserError):
            wizard.create_entries()

        # 20 hours to invoice on 2020-01-07
        wizard.date = fields.Date.to_date('2020-01-07')
        self.assertRecordValues(self.env['account.move'].search(wizard.create_entries()['domain']).line_ids, [
            # reverse move lines
            {'account_id': self.account_revenue.id, 'debit': 900, 'credit': 0},
            {'account_id': wizard.account_id.id, 'debit': 0, 'credit': 900},
            # move lines
            {'account_id': self.account_revenue.id, 'debit': 0, 'credit': 900},
            {'account_id': wizard.account_id.id, 'debit': 900, 'credit': 0},
        ])

        # nothing to invoice on 2020-01-05
        wizard.date = fields.Date.to_date('2020-01-09')
        with self.assertRaises(UserError):
            wizard.create_entries()
