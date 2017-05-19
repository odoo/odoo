# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError, AccessError
from odoo.tools import pycompat

from .test_sale_common import TestSale


class TestSaleOrder(TestSale):
    def test_sale_order(self):
        """ Test the sales order flow (invoicing and quantity updates)
            - Invoice repeatedly while varrying delivered quantities and check that invoice are always what we expect
        """
        # DBO TODO: validate invoice and register payments
        inv_obj = self.env['account.invoice']
        so = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
            'order_line': [(0, 0, {'name': p.name, 'product_id': p.id, 'product_uom_qty': 2, 'product_uom': p.uom_id.id, 'price_unit': p.list_price}) for (_, p) in pycompat.items(self.products)],
            'pricelist_id': self.env.ref('product.list0').id,
        })
        self.assertEqual(so.amount_total, sum([2 * p.list_price for (k, p) in pycompat.items(self.products)]), 'Sale: total amount is wrong')

        # send quotation
        so.force_quotation_send()
        self.assertTrue(so.state == 'sent', 'Sale: state after sending is wrong')

        # confirm quotation
        so.action_confirm()
        self.assertTrue(so.state == 'sale')
        self.assertTrue(so.invoice_status == 'to invoice')

        # create invoice: only 'invoice on order' products are invoiced
        inv_id = so.action_invoice_create()
        inv = inv_obj.browse(inv_id)
        self.assertEqual(len(inv.invoice_line_ids), 2, 'Sale: invoice is missing lines')
        self.assertEqual(inv.amount_total, sum([2 * p.list_price if p.invoice_policy == 'order' else 0 for (k, p) in pycompat.items(self.products)]), 'Sale: invoice total amount is wrong')
        self.assertTrue(so.invoice_status == 'no', 'Sale: SO status after invoicing should be "nothing to invoice"')
        self.assertTrue(len(so.invoice_ids) == 1, 'Sale: invoice is missing')

        # deliver lines except 'time and material' then invoice again
        for line in so.order_line:
            line.qty_delivered = 2 if line.product_id.expense_policy=='no' else 0
        self.assertTrue(so.invoice_status == 'to invoice', 'Sale: SO status after delivery should be "to invoice"')
        inv_id = so.action_invoice_create()
        inv = inv_obj.browse(inv_id)
        self.assertEqual(len(inv.invoice_line_ids), 2, 'Sale: second invoice is missing lines')
        self.assertEqual(inv.amount_total, sum([2 * p.list_price if p.invoice_policy == 'delivery' else 0 for (k, p) in pycompat.items(self.products)]), 'Sale: second invoice total amount is wrong')
        self.assertTrue(so.invoice_status == 'invoiced', 'Sale: SO status after invoicing everything should be "invoiced"')
        self.assertTrue(len(so.invoice_ids) == 2, 'Sale: invoice is missing')
        # go over the sold quantity
        for line in so.order_line:
            if line.product_id == self.products['serv_order']:
                line.qty_delivered = 10
        self.assertTrue(so.invoice_status == 'upselling', 'Sale: SO status after increasing delivered qty higher than ordered qty should be "upselling"')

        # upsell and invoice
        for line in so.order_line:
            if line.product_id == self.products['serv_order']:
                line.product_uom_qty = 10
        inv_id = so.action_invoice_create()
        inv = inv_obj.browse(inv_id)
        self.assertEqual(len(inv.invoice_line_ids), 1, 'Sale: third invoice is missing lines')
        self.assertEqual(inv.amount_total, 8 * self.products['serv_order'].list_price, 'Sale: second invoice total amount is wrong')
        self.assertTrue(so.invoice_status == 'invoiced', 'Sale: SO status after invoicing everything (including the upsel) should be "invoiced"')

    def test_unlink_cancel(self):
        """ Test deleting and cancelling sales orders depending on their state and on the user's rights """
        so = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
            'order_line': [(0, 0, {'name': p.name, 'product_id': p.id, 'product_uom_qty': 2, 'product_uom': p.uom_id.id, 'price_unit': p.list_price}) for (_, p) in pycompat.items(self.products)],
            'pricelist_id': self.env.ref('product.list0').id,
        })

        # SO in state 'draft' can be deleted
        so_copy = so.copy()
        with self.assertRaises(AccessError):
            so_copy.sudo(self.user).unlink()
        self.assertTrue(so_copy.sudo(self.manager).unlink(), 'Sale: deleting a quotation should be possible')

        # SO in state 'cancel' can be deleted
        so_copy = so.copy()
        so_copy.action_confirm()
        self.assertTrue(so_copy.state == 'sale', 'Sale: SO should be in state "sale"')
        so_copy.action_cancel()
        self.assertTrue(so_copy.state == 'cancel', 'Sale: SO should be in state "cancel"')
        with self.assertRaises(AccessError):
            so_copy.sudo(self.user).unlink()
        self.assertTrue(so_copy.sudo(self.manager).unlink(), 'Sale: deleting a cancelled SO should be possible')

        # SO in state 'sale' or 'done' cannot be deleted
        so.action_confirm()
        self.assertTrue(so.state == 'sale', 'Sale: SO should be in state "sale"')
        with self.assertRaises(UserError):
            so.sudo(self.manager).unlink()

        so.action_done()
        self.assertTrue(so.state == 'done', 'Sale: SO should be in state "done"')
        with self.assertRaises(UserError):
            so.sudo(self.manager).unlink()

    def test_cost_invoicing(self):
        """ Test confirming a vendor invoice to reinvoice cost on the so """
        serv_cost = self.env.ref('product.service_cost_01')
        prod_gap = self.env.ref('product.product_product_1')
        so = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
            'order_line': [(0, 0, {'name': prod_gap.name, 'product_id': prod_gap.id, 'product_uom_qty': 2, 'product_uom': prod_gap.uom_id.id, 'price_unit': prod_gap.list_price})],
            'pricelist_id': self.env.ref('product.list0').id,
        })
        so.action_confirm()
        so._create_analytic_account()
        inv_partner = self.env.ref('base.res_partner_2')
        company = self.env.ref('base.main_company')
        journal = self.env['account.journal'].create({'name': 'Purchase Journal - Test', 'code': 'STPJ', 'type': 'purchase', 'company_id': company.id})
        account_payable = self.env['account.account'].create({'code': 'X1111', 'name': 'Sale - Test Payable Account', 'user_type_id': self.env.ref('account.data_account_type_payable').id, 'reconcile': True})
        account_income = self.env['account.account'].create({'code': 'X1112', 'name': 'Sale - Test Account', 'user_type_id': self.env.ref('account.data_account_type_direct_costs').id})
        invoice_vals = {
            'name': '',
            'type': 'in_invoice',
            'partner_id': inv_partner.id,
            'invoice_line_ids': [(0, 0, {'name': serv_cost.name, 'product_id': serv_cost.id, 'quantity': 2, 'uom_id': serv_cost.uom_id.id, 'price_unit': serv_cost.standard_price, 'account_analytic_id': so.project_id.id, 'account_id': account_income.id})],
            'account_id': account_payable.id,
            'journal_id': journal.id,
            'currency_id': company.currency_id.id,
        }
        inv = self.env['account.invoice'].create(invoice_vals)
        inv.action_invoice_open()
        sol = so.order_line.filtered(lambda l: l.product_id == serv_cost)
        self.assertTrue(sol, 'Sale: cost invoicing does not add lines when confirming vendor invoice')
        self.assertTrue(sol.price_unit == 160 and sol.qty_delivered == 2 and sol.product_uom_qty == sol.qty_invoiced == 0, 'Sale: line is wrong after confirming vendor invoice')
