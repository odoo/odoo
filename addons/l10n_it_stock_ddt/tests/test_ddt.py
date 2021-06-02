# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.sale.tests.test_sale_common import TestSale
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestDDT(TestSale):

    def test_00_ddt_flow(self):
        """
            We confirm a sale order and handle its delivery partially.
            This should have created a DDT number and when we generate and the invoice,
            the delivery should be linked to it as DDT.
        """
        self.so = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
            'order_line': [(0, 0, {'name': p.name, 'product_id': p.id, 'product_uom_qty': 5, 'product_uom': p.uom_id.id,
                                   'price_unit': p.list_price, 'tax_id': self.env.company.account_sale_tax_id}) for p in self.products.values()],
            'pricelist_id': self.env.ref('product.list0').id,
            'picking_policy': 'direct',
        })
        self.so.company_id.country_id = self.env.ref('base.it')
        self.so.action_confirm()

        # deliver partially
        pick = self.so.picking_ids
        pick.move_lines.write({'quantity_done': 1})
        wiz_act = pick.button_validate()
        wiz = self.env[wiz_act['res_model']].browse(wiz_act['res_id'])
        wiz.process()

        self.assertTrue(pick.l10n_it_ddt_number, 'The outgoing picking should have a DDT number')
        self.inv1 = self.so._create_invoices()
        self.inv1.action_post()
        self.assertEqual(self.inv1.l10n_it_ddt_ids.ids, pick.ids, 'DDT should be linked to the invoice')

        # deliver partially
        pickx1 = self.so.picking_ids.filtered(lambda p: p.state != 'done')
        pickx1.move_lines.write({'quantity_done': 1})
        wiz_act = pickx1.button_validate()
        wiz = self.env[wiz_act['res_model']].browse(wiz_act['res_id'])
        wiz.process()

        # and again
        pickx2 = self.so.picking_ids.filtered(lambda p: p.state != 'done')
        pickx2.move_lines.write({'quantity_done': 2})
        wiz_act = pickx2.button_validate()
        wiz = self.env[wiz_act['res_model']].browse(wiz_act['res_id'])
        wiz.process()

        self.inv2 = self.so._create_invoices()
        self.inv2.action_post()
        self.assertEqual(self.inv2.l10n_it_ddt_ids.ids, (pickx1 | pickx2).ids, 'DDTs should be linked to the invoice')
