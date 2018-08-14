# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import fields
from odoo.tests.common import TransactionCase
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

class TestOnchangeProductId(TransactionCase):
    """Test that when an included tax is mapped by a fiscal position, the included tax must be
    subtracted to the price of the product.
    """

    def setUp(self):
        super(TestOnchangeProductId, self).setUp()
        self.fiscal_position_model = self.env['account.fiscal.position']
        self.fiscal_position_tax_model = self.env['account.fiscal.position.tax']
        self.tax_model = self.env['account.tax']
        self.po_model = self.env['purchase.order']
        self.po_line_model = self.env['purchase.order.line']
        self.res_partner_model = self.env['res.partner']
        self.product_tmpl_model = self.env['product.template']
        self.product_model = self.env['product.product']
        self.product_uom_model = self.env['uom.uom']
        self.supplierinfo_model = self.env["product.supplierinfo"]

    def test_onchange_product_id(self):

        uom_id = self.product_uom_model.search([('name', '=', 'Unit(s)')])[0]

        partner_id = self.res_partner_model.create(dict(name="George"))
        tax_include_id = self.tax_model.create(dict(name="Include tax",
                                                    amount='21.00',
                                                    price_include=True,
                                                    type_tax_use='purchase'))
        tax_exclude_id = self.tax_model.create(dict(name="Exclude tax",
                                                    amount='0.00',
                                                    type_tax_use='purchase'))
        supplierinfo_vals = {
            'name': partner_id.id,
            'price': 121.0,
        }

        supplierinfo = self.supplierinfo_model.create(supplierinfo_vals)

        product_tmpl_id = self.product_tmpl_model.create(dict(name="Voiture",
                                                              list_price=121,
                                                              seller_ids=[(6, 0, [supplierinfo.id])],
                                                              supplier_taxes_id=[(6, 0, [tax_include_id.id])]))
        product_id = self.product_model.create(dict(product_tmpl_id=product_tmpl_id.id))

        fp_id = self.fiscal_position_model.create(dict(name="fiscal position", sequence=1))

        fp_tax_id = self.fiscal_position_tax_model.create(dict(position_id=fp_id.id,
                                                               tax_src_id=tax_include_id.id,
                                                               tax_dest_id=tax_exclude_id.id))
        po_vals = {
            'partner_id': partner_id.id,
            'fiscal_position_id': fp_id.id,
            'order_line': [
                (0, 0, {
                    'name': product_id.name,
                    'product_id': product_id.id,
                    'product_qty': 1.0,
                    'product_uom': uom_id.id,
                    'price_unit': 121.0,
                    'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                })],
        }
        po = self.po_model.create(po_vals)

        po_line = po.order_line[0]
        po_line.onchange_product_id()
        self.assertEquals(100, po_line.price_unit, "The included tax must be subtracted to the price")

        supplierinfo.write({'min_qty': 24})
        po_line.write({'product_qty': 20})
        po_line._onchange_quantity()
        self.assertEquals(0, po_line.price_unit, "Unit price should be reset to 0 since the supplier supplies minimum of 24 quantities")

        po_line.write({'product_qty': 3, 'product_uom': self.ref("uom.product_uom_dozen")})
        po_line._onchange_quantity()
        self.assertEquals(1200, po_line.price_unit, "Unit price should be 1200 for one Dozen")

        product_ipad = self.env.ref('product.product_product_4')
        po_line2 = self.po_line_model.create({
            'name': product_ipad.name,
            'product_id': product_ipad.id,
            'order_id': po.id,
            'product_qty': 5,
            'product_uom': uom_id.id,
            'price_unit': 100.0,
            'date_planned': fields.Date().today()
        })
        po_line2.onchange_product_id()
        self.assertEquals(0, po_line2.price_unit, "No vendor supplies this product, hence unit price should be set to 0")
