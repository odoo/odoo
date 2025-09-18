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
        self.env.user.group_ids += self.env.ref('uom.group_uom')

        uom_id = self.product_uom_model.search([('name', '=', 'Units')])[0]

        partner_id = self.res_partner_model.create(dict(name="George"))
        fp_id = self.fiscal_position_model.create(dict(name="fiscal position", sequence=1))
        tax_include_id = self.tax_model.create(dict(name="Include tax",
                                                    amount='21.00',
                                                    price_include_override='tax_included',
                                                    type_tax_use='purchase'))
        tax_exclude_id = self.tax_model.create(dict(name="Exclude tax",
                                                    fiscal_position_ids=fp_id,
                                                    original_tax_ids=tax_include_id,
                                                    amount='0.00',
                                                    type_tax_use='purchase'))

        product_tmpl_id = self.product_tmpl_model.create(dict(name="Voiture",
                                                              list_price=121,
                                                              supplier_taxes_id=[(6, 0, [tax_include_id.id])]))
        supplierinfo_vals = {
            'product_id': product_tmpl_id.product_variant_id.id,
            'partner_id': partner_id.id,
            'price': 121.0,
        }

        supplierinfo = self.supplierinfo_model.create(supplierinfo_vals)
        product_id = product_tmpl_id.product_variant_id

        # Use Form to properly trigger computed fields for tax-inclusive price conversion
        with Form(self.po_model) as po_form:
            po_form.partner_id = partner_id
            po_form.fiscal_position_id = fp_id
            with po_form.line_ids.new() as po_line_form:
                po_line_form.product_id = product_id
                po_line_form.product_qty = 1.0
                po_line_form.product_uom_id = uom_id
        po = po_form.save()

        po_line = po.line_ids[0]
        # Computed fields handle the tax-inclusive price conversion automatically
        self.assertEqual(100, po_line.price_unit, "The included tax must be subtracted to the price")

        supplierinfo.write({'min_qty': 24})
        po_line.write({'product_qty': 20})
        self.assertEqual(0, po_line.price_unit, "Unit price should be reset to 0 since the supplier supplies minimum of 24 quantities")

        po_line.write({'product_qty': 3, 'product_uom_id': self.ref("uom.product_uom_dozen")})
        self.assertEqual(1200, po_line.price_unit, "Unit price should be 1200 for one Dozen")
        ipad_lot = self.env['uom.uom'].create({
            'name': 'Ipad',
        })
        ipad_lot_10 = self.env['uom.uom'].create({
            'name': '10 Ipad',
            'relative_factor': 10,
            'relative_uom_id': ipad_lot.id,
        })
        product_ipad = self.env['product.product'].create({
            'name': 'Conference Chair',
            'standard_price': 100,
            'uom_id': ipad_lot.id,
        })
        # Use Form to create line - this properly triggers computed fields with UoM conversion
        with Form(po) as po_form:
            with po_form.line_ids.new() as po_line_form:
                po_line_form.product_id = product_ipad
                po_line_form.product_qty = 5
                po_line_form.product_uom_id = ipad_lot_10  # UoM is 10x the base
        po = po_form.save()

        # The price should be computed from standard_price converted to the line UoM
        # standard_price is 100 per 1 Ipad, so for 10 Ipad UoM it should be 1000
        po_line2 = po.line_ids.filtered(lambda l: l.product_id == product_ipad)
        self.assertEqual(1000, po_line2.price_unit, "Price for 10 Ipad UoM should be 10x the standard_price")
