# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestOnchangeProductId(TransactionCase):
    """Test that when an included tax is mapped by a fiscal position, the included tax must be
    subtracted to the price of the product.
    """

    def setUp(self):
        super(TestOnchangeProductId, self).setUp()
        self.fiscal_position_model = self.env['account.fiscal.position']
        self.fiscal_position_tax_model = self.env['account.fiscal.position.tax']
        self.tax_model = self.env['account.tax']
        self.so_model = self.env['sale.order']
        self.po_line_model = self.env['sale.order.line']
        self.res_partner_model = self.env['res.partner']
        self.product_tmpl_model = self.env['product.template']
        self.product_model = self.env['product.product']
        self.product_uom_model = self.env['product.uom']
        self.supplierinfo_model = self.env["product.supplierinfo"]
        self.pricelist_model = self.env['product.pricelist']

    def test_onchange_product_id(self):

        uom_id = self.product_uom_model.search([('name', '=', 'Unit(s)')])[0]
        pricelist = self.pricelist_model.search([('name', '=', 'Public Pricelist')])[0]

        partner_id = self.res_partner_model.create(dict(name="George"))
        tax_include_id = self.tax_model.create(dict(name="Include tax",
                                                    amount='21.00',
                                                    price_include=True,
                                                    type_tax_use='sale'))
        tax_exclude_id = self.tax_model.create(dict(name="Exclude tax",
                                                    amount='0.00',
                                                    type_tax_use='sale'))

        product_tmpl_id = self.product_tmpl_model.create(dict(name="Voiture",
                                                              list_price=121,
                                                              taxes_id=[(6, 0, [tax_include_id.id])]))

        product_id = self.product_model.create(dict(product_tmpl_id=product_tmpl_id.id))

        fp_id = self.fiscal_position_model.create(dict(name="fiscal position", sequence=1))

        fp_tax_id = self.fiscal_position_tax_model.create(dict(position_id=fp_id.id,
                                                               tax_src_id=tax_include_id.id,
                                                               tax_dest_id=tax_exclude_id.id))
        so_vals = {
            'partner_id': partner_id.id,
            'pricelist_id': pricelist.id,
            'fiscal_position_id': fp_id.id,
            'order_line': [
                (0, 0, {
                    'name': product_id.name,
                    'product_id': product_id.id,
                    'product_uom_qty': 1.0,
                    'product_uom': uom_id.id,
                    'price_unit': 121.0
                })
            ]
        }

        so = self.so_model.create(so_vals)

        so_line = so.order_line[0]
        so_line.product_id_change()
        self.assertEquals(100, so_line.price_unit, "The included tax must be subtracted to the price")
