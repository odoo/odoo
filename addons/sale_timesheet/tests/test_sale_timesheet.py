# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tools import float_is_zero

from odoo.addons.sale.tests.test_sale_common import TestSale


class TestSaleTimesheet(TestSale):

    def setUp(self):
        super(TestSaleTimesheet, self).setUp()
        # link hr employee to res.users of sale tests
        self.employee_user = self.env['hr.employee'].create({
            'name': 'Employee User',
            'user_id': self.user.id,
        })
        self.employee_manager = self.env['hr.employee'].create({
            'name': 'Employee Manager',
            'user_id': self.manager.id,
        })

    def test_timesheet_order(self):
        """ Test timesheet invoicing with 'invoice on order' timetracked products """
        # intial so
        prod_ts = self.env.ref('product.service_order_01')
        so_vals = {
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
            'order_line': [(0, 0, {'name': prod_ts.name, 'product_id': prod_ts.id, 'product_uom_qty': 50, 'product_uom': prod_ts.uom_id.id, 'price_unit': prod_ts.list_price})],
            'pricelist_id': self.env.ref('product.list0').id,
        }
        so = self.env['sale.order'].create(so_vals)
        so.action_confirm()
        so.action_invoice_create()

        # let's log some timesheets
        self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': so.project_project_id.id,
            'unit_amount': 10.5,
            'employee_id': self.employee_user.id,
        })
        self.assertEqual(so.order_line.qty_delivered, 10.5, 'Sale Timesheet: timesheet does not increase delivered quantity on so line')
        self.assertEqual(so.invoice_status, 'invoiced', 'Sale Timesheet: "invoice on order" timesheets should not modify the invoice_status of the so')

        self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': so.project_project_id.id,
            'unit_amount': 39.5,
            'employee_id': self.employee_user.id,
        })
        self.assertEqual(so.order_line.qty_delivered, 50, 'Sale Timesheet: timesheet does not increase delivered quantity on so line')
        self.assertEqual(so.invoice_status, 'invoiced', 'Sale Timesheet: "invoice on order" timesheets should not modify the invoice_status of the so')

        self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': so.project_project_id.id,
            'unit_amount': 10,
            'employee_id': self.employee_user.id,
        })
        self.assertEqual(so.order_line.qty_delivered, 60, 'Sale Timesheet: timesheet does not increase delivered quantity on so line')
        self.assertEqual(so.invoice_status, 'upselling', 'Sale Timesheet: "invoice on order" timesheets should not modify the invoice_status of the so')

    def test_timesheet_delivery(self):
        """ Test timesheet invoicing with 'invoice on delivery' timetracked products """
        inv_obj = self.env['account.invoice']
        # intial so
        prod_ts = self.env.ref('product.product_product_2')
        so_vals = {
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
            'order_line': [(0, 0, {'name': prod_ts.name, 'product_id': prod_ts.id, 'product_uom_qty': 50, 'product_uom': prod_ts.uom_id.id, 'price_unit': prod_ts.list_price})],
            'pricelist_id': self.env.ref('product.list0').id,
        }
        so = self.env['sale.order'].create(so_vals)
        so.action_confirm()
        self.assertEqual(so.invoice_status, 'no', 'Sale Timesheet: "invoice on delivery" should not need to be invoiced on so confirmation')
        # let's log some timesheets
        self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': so.project_project_id.id,
            'unit_amount': 10.5,
            'employee_id': self.employee_manager.id,
        })
        self.assertEqual(so.invoice_status, 'to invoice', 'Sale Timesheet: "invoice on delivery" timesheets should set the so in "to invoice" status when logged')
        inv_id = so.action_invoice_create()
        inv = inv_obj.browse(inv_id)
        self.assertTrue(float_is_zero(inv.amount_total - so.order_line.price_unit * 10.5, precision_digits=2), 'Sale: invoice generation on timesheets product is wrong')

        self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': so.project_project_id.id,
            'unit_amount': 39.5,
            'employee_id': self.employee_user.id,
        })
        self.assertEqual(so.invoice_status, 'to invoice', 'Sale Timesheet: "invoice on delivery" timesheets should not modify the invoice_status of the so')
        so.action_invoice_create()
        self.assertEqual(so.invoice_status, 'invoiced', 'Sale Timesheet: "invoice on delivery" timesheets should be invoiced completely by now')

        self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': so.project_project_id.id,
            'unit_amount': 10,
            'employee_id': self.employee_user.id,
        })
        self.assertEqual(so.invoice_status, 'to invoice', 'Sale Timesheet: supplementary timesheets do not change the status of the SO')

    def test_timesheet_uom(self):
        """ Test timesheet invoicing and uom conversion """
        # intial so
        prod_ts = self.env.ref('product.product_product_2')
        uom_days = self.env.ref('product.product_uom_day')
        so_vals = {
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
            'order_line': [(0, 0, {'name': prod_ts.name, 'product_id': prod_ts.id, 'product_uom_qty': 5, 'product_uom': uom_days.id, 'price_unit': prod_ts.list_price})],
            'pricelist_id': self.env.ref('product.list0').id,
        }
        so = self.env['sale.order'].create(so_vals)
        so.action_confirm()
        # let's log some timesheets
        self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': so.project_project_id.id,
            'unit_amount': 16,
            'employee_id': self.employee_manager.id,
        })
        self.assertEqual(so.order_line.qty_delivered, 2, 'Sale: uom conversion of timesheets is wrong')

        self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': so.project_project_id.id,
            'unit_amount': 24,
            'employee_id': self.employee_user.id,
        })
        so.action_invoice_create()
        self.assertEqual(so.invoice_status, 'invoiced', 'Sale Timesheet: "invoice on delivery" timesheets should not modify the invoice_status of the so')
