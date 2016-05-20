# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp.exceptions import UserError, AccessError

from test_sale_common import TestSale


class TestSaleOrder(TestSale):
    def test_sale_order(self):
        """ Test the sale order flow (invoicing and quantity updates)
            - Invoice repeatedly while varrying delivered quantities and check that invoice are always what we expect
        """
        # DBO TODO: validate invoice and register payments
        inv_obj = self.env['account.invoice']
        so = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
            'order_line': [(0, 0, {'name': p.name, 'product_id': p.id, 'product_uom_qty': 2, 'product_uom': p.uom_id.id, 'price_unit': p.list_price}) for (_, p) in self.products.iteritems()],
            'pricelist_id': self.env.ref('product.list0').id,
        })
        self.assertEqual(so.amount_total, sum([2 * p.list_price for (k, p) in self.products.iteritems()]), 'Sale: total amount is wrong')

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
        self.assertEqual(inv.amount_total, sum([2 * p.list_price if p.invoice_policy == 'order' else 0 for (k, p) in self.products.iteritems()]), 'Sale: invoice total amount is wrong')
        self.assertTrue(so.invoice_status == 'no', 'Sale: SO status after invoicing should be "nothing to invoice"')
        self.assertTrue(len(so.invoice_ids) == 1, 'Sale: invoice is missing')

        # deliver lines except 'time and material' then invoice again
        for line in so.order_line:
            line.qty_delivered = 2 if line.product_id.invoice_policy in ['order', 'delivery'] else 0
        self.assertTrue(so.invoice_status == 'to invoice', 'Sale: SO status after delivery should be "to invoice"')
        inv_id = so.action_invoice_create()
        inv = inv_obj.browse(inv_id)
        self.assertEqual(len(inv.invoice_line_ids), 2, 'Sale: second invoice is missing lines')
        self.assertEqual(inv.amount_total, sum([2 * p.list_price if p.invoice_policy == 'delivery' else 0 for (k, p) in self.products.iteritems()]), 'Sale: second invoice total amount is wrong')
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
        """ Test deleting and cancelling sale orders depending on their state and on the user's rights """
        so = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
            'order_line': [(0, 0, {'name': p.name, 'product_id': p.id, 'product_uom_qty': 2, 'product_uom': p.uom_id.id, 'price_unit': p.list_price}) for (_, p) in self.products.iteritems()],
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
