# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import fields
from odoo.tests import Form, TransactionCase
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class TestOnchangeProductId(TransactionCase):
    """Test that when an included tax is mapped by a fiscal position, the included tax must be
    subtracted to the price of the product.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.country_id = cls.env.ref('base.us')
        cls.fiscal_position_model = cls.env['account.fiscal.position']
        cls.fiscal_position_tax_model = cls.env['account.fiscal.position.tax']
        cls.tax_model = cls.env['account.tax']
        cls.po_model = cls.env['purchase.order']
        cls.po_line_model = cls.env['purchase.order.line']
        cls.res_partner_model = cls.env['res.partner']
        cls.product_tmpl_model = cls.env['product.template']
        cls.product_model = cls.env['product.product']
        cls.product_uom_model = cls.env['uom.uom']
        cls.supplierinfo_model = cls.env["product.supplierinfo"]
        cls.env['account.tax.group'].create(
            {'name': 'Test Account Tax Group', 'company_id': cls.env.company.id}
        )

    def test_onchange_product_id(self):
        # Required for `product_uom` to be visible in the view
        self.env.user.groups_id += self.env.ref('uom.group_uom')

        uom_id = self.product_uom_model.search([('name', '=', 'Units')])[0]

        partner_id = self.res_partner_model.create(dict(name="George"))
        tax_include_id = self.tax_model.create(dict(name="Include tax",
                                                    amount='21.00',
                                                    price_include_override='tax_included',
                                                    type_tax_use='purchase'))
        tax_exclude_id = self.tax_model.create(dict(name="Exclude tax",
                                                    amount='0.00',
                                                    type_tax_use='purchase'))
        supplierinfo_vals = {
            'partner_id': partner_id.id,
            'price': 121.0,
        }

        supplierinfo = self.supplierinfo_model.create(supplierinfo_vals)

        product_tmpl_id = self.product_tmpl_model.create(dict(name="Voiture",
                                                              list_price=121,
                                                              seller_ids=[(6, 0, [supplierinfo.id])],
                                                              supplier_taxes_id=[(6, 0, [tax_include_id.id])]))
        product_id = product_tmpl_id.product_variant_id

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
        self.assertEqual(100, po_line.price_unit, "The included tax must be subtracted to the price")

        supplierinfo.write({'min_qty': 24})
        po_line.write({'product_qty': 20})
        self.assertEqual(0, po_line.price_unit, "Unit price should be reset to 0 since the supplier supplies minimum of 24 quantities")

        po_line.write({'product_qty': 3, 'product_uom': self.ref("uom.product_uom_dozen")})
        self.assertEqual(1200, po_line.price_unit, "Unit price should be 1200 for one Dozen")
        ipad_uom = self.env['uom.category'].create({'name': 'Ipad Unit'})
        ipad_lot = self.env['uom.uom'].create({
            'name': 'Ipad',
            'category_id': ipad_uom.id,
            'uom_type': 'reference',
            'rounding': 0.001
        })
        ipad_lot_10 = self.env['uom.uom'].create({
            'name': '10 Ipad',
            'category_id': ipad_uom.id,
            'uom_type': 'bigger',
            'rounding': 0.001,
            "factor_inv": 10
        })
        product_ipad = self.env['product.product'].create({
            'name': 'Conference Chair',
            'standard_price': 100,
            'uom_id': ipad_lot.id,
            'uom_po_id': ipad_lot.id,
        })
        po_line2 = self.po_line_model.create({
            'name': product_ipad.name,
            'product_id': product_ipad.id,
            'order_id': po.id,
            'product_qty': 5,
            'product_uom': ipad_uom.id,
            'date_planned': fields.Date().today()
        })

        po_line2.onchange_product_id()
        self.assertEqual(100, po_line2.price_unit, "No vendor supplies this product, hence unit price should be set to 100")

        po_form = Form(po)
        with po_form.order_line.edit(1) as order_line:
            order_line.product_uom = ipad_lot_10
        po_form.save()
        self.assertEqual(1000, po_line2.price_unit, "The product_uom is multiplied by 10, hence unit price should be set to 1000")
