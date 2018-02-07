# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sale.tests.test_sale_common import TestSale
from odoo.exceptions import UserError
from odoo.tools import float_repr
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestSaleTimesheet(TestSale):

    def setUp(self):
        super(TestSaleTimesheet, self).setUp()

        # NOTE JEM
        # The tests below are based on the `base.rateUSD` currency rate. It
        # is required to remove the `base.rateUSDbis` to avoid rounding error
        # after the 6 june of current year.
        self.env.ref('base.rateUSDbis').unlink()

        # create project
        self.project = self.env['project.project'].create({
            'name': 'Project for my timesheets',
            'allow_timesheets': True,
        })

        # create service products
        self.product_deliver = self.env['product.product'].create({
            'name': "Delivered Service",
            'standard_price': 30,
            'list_price': 90,
            'type': 'service',
            'invoice_policy': 'delivery',
            'uom_id': self.env.ref('product.product_uom_hour').id,
            'uom_po_id': self.env.ref('product.product_uom_hour').id,
            'default_code': 'SERV-DELI',
            'service_type': 'timesheet',
            'service_tracking': 'task_global_project',
            'project_id': self.project.id,
        })

        self.product_order = self.env['product.product'].create({
            'name': "Ordered Service",
            'standard_price': 37,
            'list_price': 51,
            'type': 'service',
            'invoice_policy': 'order',
            'uom_id': self.env.ref('product.product_uom_hour').id,
            'uom_po_id': self.env.ref('product.product_uom_hour').id,
            'default_code': 'SERV-ORDER',
            'service_type': 'timesheet',
            'service_tracking': 'task_global_project',
            'project_id': self.project.id,
        })

        # pricelists
        self.pricelist_usd = self.env['product.pricelist'].create({
            'name': 'USD pricelist',
            'active': True,
            'currency_id': self.env.ref('base.USD').id,
            'company_id': self.env.user.company_id.id,
        })
        self.pricelist_eur = self.env['product.pricelist'].create({
            'name': 'EUR pricelist',
            'active': True,
            'currency_id': self.env.ref('base.EUR').id,
            'company_id': self.env.user.company_id.id,
        })
        # partners
        self.partner_usd = self.env['res.partner'].create({
            'name': 'Cool Partner in USD',
            'email': 'partner.usd@test.com',
            'property_product_pricelist': self.pricelist_usd.id,
        })
        self.partner_eur = self.env['res.partner'].create({
            'name': 'Cool partner in EUR',
            'email': 'partner.eur@test.com',
            'property_product_pricelist': self.pricelist_eur.id,
        })

    def test_revenue(self):
        """ Create a SO with 2 lines : one for a delivered service, one for a ordered service. Confirm
            and invoice it. For this, we use a partner having the same currency as the current company.
            3 timesheets are logged before invoicing : 2 for delivered, 1 for ordered.
        """
        # create SO and confirm it
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_usd.id,
            'partner_invoice_id': self.partner_usd.id,
            'partner_shipping_id': self.partner_usd.id,
            'pricelist_id': self.pricelist_usd.id,
        })
        sale_order_line_delivered = self.env['sale.order.line'].create({
            'name': self.product_deliver.name,
            'product_id': self.product_deliver.id,
            'product_uom_qty': 12,
            'product_uom': self.product_deliver.uom_id.id,
            'price_unit': self.product_deliver.list_price,
            'order_id': sale_order.id,
        })
        sale_order_line_ordered = self.env['sale.order.line'].create({
            'name': self.product_order.name,
            'product_id': self.product_order.id,
            'product_uom_qty': 7,
            'product_uom': self.product_order.uom_id.id,
            'price_unit': self.product_order.list_price,
            'order_id': sale_order.id,
        })
        sale_order_line_ordered.product_id_change()
        sale_order_line_delivered.product_id_change()
        sale_order.action_confirm()

        # log timesheet on tasks
        task_delivered = self.env['project.task'].search([('sale_line_id', '=', sale_order_line_delivered.id)])
        task_ordered = self.env['project.task'].search([('sale_line_id', '=', sale_order_line_ordered.id)])

        timesheet1 = self.env['account.analytic.line'].create({
            'name': 'ts 1',
            'unit_amount': 5,
            'task_id': task_delivered.id,
            'project_id': task_delivered.project_id.id,
        })
        timesheet2 = self.env['account.analytic.line'].create({
            'name': 'ts 2',
            'unit_amount': 2,
            'task_id': task_delivered.id,
            'project_id': task_delivered.project_id.id,
        })
        timesheet3 = self.env['account.analytic.line'].create({
            'name': 'ts 3',
            'unit_amount': 3,
            'task_id': task_ordered.id,
            'project_id': task_ordered.project_id.id,
        })

        # check we don't compare apples and pears
        self.assertEquals(timesheet1.currency_id, sale_order.currency_id, 'Currencies should not differ (%s vs %s)' % (timesheet1.currency_id.name, sale_order.currency_id.name))
        # check theorical revenue
        self.assertEquals(timesheet1.timesheet_invoice_type, 'billable_time', "Billable type on task from delivered service should be 'billabe time'")
        self.assertEquals(timesheet2.timesheet_invoice_type, 'billable_time', "Billable type on task from delivered service should be 'billabe time'")
        self.assertEquals(timesheet3.timesheet_invoice_type, 'billable_fixed', "Billable type on task from ordered service should be 'billabe fixed'")
        self.assertEquals(timesheet1.timesheet_invoice_id, self.env['account.invoice'])
        self.assertEquals(timesheet2.timesheet_invoice_id, self.env['account.invoice'])
        self.assertEquals(timesheet3.timesheet_invoice_id, self.env['account.invoice'])
        # Hours * SO Line price_unit * (1-discount)
        self.assertEquals(timesheet1.timesheet_revenue, 450, "Revenue computation does not return the correct amount !")
        self.assertEquals(timesheet2.timesheet_revenue, 180, "Revenue computation does not return the correct amount !")
        # MIN (
        #   2 * 90 * (1 - 0.0) = 180
        #   (12 * 90) - 450 = 1080
        # )
        self.assertEquals(timesheet3.timesheet_revenue, 153, "Revenue computation does not return the correct amount !")

        # invoice the SO
        context = {
            "active_model": 'sale.order',
            "active_ids": [sale_order.id],
            "active_id": sale_order.id,
            'open_invoices': True,
        }
        payment = self.env['sale.advance.payment.inv'].create({
            'advance_payment_method': 'delivered',
        })
        action_invoice = payment.with_context(context).create_invoices()
        invoice_id = action_invoice['res_id']
        invoice = self.env['account.invoice'].browse(invoice_id)

        # check revenues have not changed
        self.assertEquals(timesheet1.timesheet_revenue, 450, "Revenue computation does not return the correct amount !")
        self.assertEquals(timesheet2.timesheet_revenue, 180, "Revenue computation does not return the correct amount !")
        self.assertEquals(timesheet3.timesheet_revenue, 153, "Revenue computation does not return the correct amount !")

        # update invoice line by setting a reduction, then validate it
        for invoice_line in invoice.invoice_line_ids:
            invoice_line.write({'price_unit': invoice_line.price_unit - 10})
        invoice.action_invoice_open()

        # check concrete revenue
        # (Total inv line / SUM(uninvoiced timesheet for delivered service) ) * timesheet line hours, so
        # (560 / 7 )* 5 = 400
        # (560 / 7) * 2 = 160
        self.assertEquals(timesheet1.timesheet_revenue, 400, "Revenue computation on invoice validation does not return the correct revenue !")
        self.assertEquals(timesheet2.timesheet_revenue, 160, "Revenue computation on invoice validation does not return the correct revenue !")
        # Since their is only one line, the total invoice line is set as revenue for ordered service
        self.assertEquals(timesheet3.timesheet_revenue, 287, "Revenue computation on invoice validation does not return the correct revenue !")

        # check the invoice is well set
        self.assertEquals(timesheet1.timesheet_invoice_id, invoice)
        self.assertEquals(timesheet2.timesheet_invoice_id, invoice)
        self.assertEquals(timesheet3.timesheet_invoice_id, invoice)

        # check that analytic line for product 'delivery' cannot be altered
        with self.assertRaises(UserError):
            timesheet1.write(dict(unit_amount=10))
        self.assertNotEquals(timesheet1.unit_amount, 10)

        # check that analytic line for product 'ordered' can be altered
        timesheet3.write(dict(unit_amount=10))
        self.assertEquals(timesheet3.unit_amount, 10)

        # check that if at least 1 analytic line is for product 'delivery', it cannot be altered
        with self.assertRaises(UserError):
            (timesheet1 + timesheet3).write(dict(unit_amount=15))
        self.assertNotEquals(timesheet1.unit_amount, 15)
        self.assertNotEquals(timesheet3.unit_amount, 15)

    def test_revenue_multi_currency(self):
        """ Create a SO with 2 lines : one for a delivered service, one for a ordered service. Confirm
            and invoice it. For this, we use a partner having a DIFFERENT currency from the current company.
            4 timesheets are logged before invoicing : 2 for delivered, 2 for ordered.
        """
        # create SO and confirm it
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_usd.id,
            'partner_invoice_id': self.partner_eur.id,
            'partner_shipping_id': self.partner_eur.id,
            'pricelist_id': self.pricelist_eur.id,
        })
        sale_order_line_delivered = self.env['sale.order.line'].create({
            'name': self.product_deliver.name,
            'product_id': self.product_deliver.id,
            'product_uom_qty': 12,
            'product_uom': self.product_deliver.uom_id.id,
            'price_unit': self.product_deliver.list_price,
            'order_id': sale_order.id,
        })
        sale_order_line_ordered = self.env['sale.order.line'].create({
            'name': self.product_order.name,
            'product_id': self.product_order.id,
            'product_uom_qty': 7,
            'product_uom': self.product_order.uom_id.id,
            'price_unit': self.product_order.list_price,
            'order_id': sale_order.id,
        })
        sale_order_line_ordered.product_id_change()
        sale_order_line_delivered.product_id_change()
        sale_order.action_confirm()

        # log timesheet on tasks
        task_delivered = self.env['project.task'].search([('sale_line_id', '=', sale_order_line_delivered.id)])
        task_ordered = self.env['project.task'].search([('sale_line_id', '=', sale_order_line_ordered.id)])

        timesheet1 = self.env['account.analytic.line'].create({
            'name': 'ts 1',
            'unit_amount': 5,
            'task_id': task_delivered.id,
            'project_id': task_delivered.project_id.id,
        })
        timesheet2 = self.env['account.analytic.line'].create({
            'name': 'ts 2',
            'unit_amount': 2,
            'task_id': task_delivered.id,
            'project_id': task_delivered.project_id.id,
        })
        timesheet3 = self.env['account.analytic.line'].create({
            'name': 'ts 3',
            'unit_amount': 3,
            'task_id': task_ordered.id,
            'project_id': task_ordered.project_id.id,
        })
        timesheet4 = self.env['account.analytic.line'].create({
            'name': 'ts 4',
            'unit_amount': 6,
            'task_id': task_ordered.id,
            'project_id': task_ordered.project_id.id,
        })

        # check theorical revenue
        # Note: conversion from EUR to USD is  *1.2833309567944147
        self.assertEquals(timesheet1.timesheet_invoice_type, 'billable_time', "Billable type on task from delivered service should be 'billabe time'")
        self.assertEquals(timesheet2.timesheet_invoice_type, 'billable_time', "Billable type on task from delivered service should be 'billabe time'")
        self.assertEquals(timesheet3.timesheet_invoice_type, 'billable_fixed', "Billable type on task from ordered service should be 'billabe fixed'")
        self.assertEquals(timesheet4.timesheet_invoice_type, 'billable_fixed', "Billable type on task from ordered service should be 'billabe fixed'")
        self.assertEquals(timesheet1.timesheet_invoice_id, self.env['account.invoice'])
        self.assertEquals(timesheet2.timesheet_invoice_id, self.env['account.invoice'])
        self.assertEquals(timesheet3.timesheet_invoice_id, self.env['account.invoice'])
        # Same computation as the test below, since revenue is stored in company currency
        self.assertEquals(timesheet1.timesheet_revenue, 450, "Revenue computation does not return the correct amount !")
        self.assertEquals(timesheet2.timesheet_revenue, 180, "Revenue computation does not return the correct amount !")
        self.assertEquals(timesheet3.timesheet_revenue, 153, "Revenue computation does not return the correct amount !")
        self.assertEquals(timesheet4.timesheet_revenue, 204, "Revenue computation does not return the correct amount !")

        # invoice the SO
        context = {
            "active_model": 'sale.order',
            "active_ids": [sale_order.id],
            "active_id": sale_order.id,
            'open_invoices': True,
        }
        payment = self.env['sale.advance.payment.inv'].create({
            'advance_payment_method': 'delivered',
        })
        action_invoice = payment.with_context(context).create_invoices()
        invoice_id = action_invoice['res_id']
        invoice = self.env['account.invoice'].browse(invoice_id)

        # update invoice line by setting a reduction, then validate it
        for invoice_line in invoice.invoice_line_ids:
            invoice_line.write({'price_unit': invoice_line.price_unit - 10})
        invoice.action_invoice_open()

        # check concrete revenue
        self.assertEquals(float_repr(timesheet1.timesheet_revenue, precision_digits=2), '385.85', "Revenue computation on invoice validation does not return the correct revenue !")
        self.assertEquals(float_repr(timesheet2.timesheet_revenue, precision_digits=2), '154.35', "Revenue computation on invoice validation does not return the correct revenue !")
        self.assertEquals(float_repr(timesheet3.timesheet_revenue, precision_digits=2), '114.50', "Revenue computation on invoice validation does not return the correct revenue !")
        self.assertEquals(float_repr(timesheet4.timesheet_revenue, precision_digits=2), '152.68', "Revenue computation on invoice validation does not return the correct revenue !")

        # check the invoice is well set
        self.assertEquals(timesheet1.timesheet_invoice_id, invoice)
        self.assertEquals(timesheet2.timesheet_invoice_id, invoice)
        self.assertEquals(timesheet3.timesheet_invoice_id, invoice)
