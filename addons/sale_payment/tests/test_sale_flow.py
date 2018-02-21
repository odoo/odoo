# -*- coding: utf-8 -*-

from odoo.addons.sale.tests.test_sale_common import TestSale

import odoo.tests


@odoo.tests.tagged('post_install', '-at_install')
class TestSaleFlow(TestSale):
    def create_so(self):
        return self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
            'order_line': [(0, 0, {'name': p.name, 'product_id': p.id, 'product_uom_qty': 1, 'product_uom': p.uom_id.id,
                                   'price_unit': p.list_price}) for p in self.products.values()],
            'pricelist_id': self.env.ref('product.list0').id,
        })

    def test_sale_state_flow(self):
        so = self.create_so()

        self.env['ir.config_parameter'].sudo().set_param('website_sale.automatic_invoice', True)

        acquirer = self.env['payment.acquirer'].search([], limit=1)

        transaction = self.env['payment.transaction'].create({
            'amount': 740.0,
            'acquirer_id': acquirer.id,
            'currency_id': so.currency_id.id,
            'partner_id': so.partner_id.id,
            'reference': so.name,
            'sale_order_ids': [(6, 0, so.ids)],
        })
        transaction.post()

        self.assertEqual(transaction.state, 'posted')
        self.assertEqual(so.state, 'sale')
        self.assertEqual(len(so.invoice_ids), 1)
        self.assertEqual(so.invoice_ids.state, 'paid')
