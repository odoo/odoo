# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests

from odoo.tests import Form

from odoo.addons.product_matrix.tests.common import TestMatrixCommon


@odoo.tests.tagged('post_install', '-at_install')
class TestPurchaseMatrixUi(TestMatrixCommon):

    def test_purchase_matrix_ui(self):
        self.start_tour("/odoo", 'purchase_matrix_tour', login="admin")

        # Ensures some dynamic create variants have been created by the matrix
        # Ensures a PO has been created with exactly x lines ...

        self.assertEqual(len(self.matrix_template.product_variant_ids), 7)
        self.assertEqual(len(self.matrix_template.product_variant_ids.product_template_attribute_value_ids), 6)
        self.assertEqual(len(self.matrix_template.attribute_line_ids.product_template_value_ids), 8)

        # check variant (PAV11, PAV21, PAV31) is not created because the two cell on it were 0
        dyn = self.matrix_template.product_variant_ids.filtered(
            lambda p: p.product_template_variant_value_ids.mapped('name') == ['PAV11', 'PAV21', 'PAV31']
        )
        self.assertFalse(dyn)

        self.env['purchase.order.line'].search([('product_id', 'in', self.matrix_template.product_variant_ids.ids)]).order_id.button_confirm()
        self.matrix_template.flush_recordset()
        self.assertEqual(round(self.matrix_template.purchased_product_qty, 2), 51.8)
        for variant in self.matrix_template.product_variant_ids:
            # 5 and 9.2 because of no variant attributes
            self.assertIn(round(variant.purchased_product_qty, 2), [5, 9.2])

        # Ensure no duplicate line has been created on the PO.
        # NB: the *2 is because the no_variant attribute doesn't create a variant
        # but still gives different order lines.
        self.assertEqual(
            len(self.env['purchase.order.line'].search([('product_id', 'in', self.matrix_template.product_variant_ids.ids)])),
            len(self.matrix_template.product_variant_ids)*2
        )

    def test_translate_never_variant_attributes_on_pol(self):
        """ Check that the attribute values set on a pol for never variant attribute are translated according to the seller language.
        """
        self.env['res.lang']._activate_lang('fr_BE')
        french_partner = self.env['res.partner'].create({
            'name': 'French Partner',
            'lang': 'fr_BE',
            'email': 'french.partner@test.com',
        })
        product_template = self.matrix_template
        product_template.with_context(lang='fr_BE').name = 'matrixFR'
        attribute_never = product_template.attribute_line_ids.attribute_id[-1]
        attribute_never.with_context(lang='fr_BE').name = 'PA4FR'
        attribute_never.value_ids[0].with_context(lang='fr_BE').name = 'PAV41FR'
        product_template.product_variant_ids = self.env['product.product'].create({'name': product_template.name})
        purchase_order = self.env['purchase.order'].create({
            'partner_id': french_partner.id,
        })
        with Form(purchase_order) as po_form:
            with po_form.order_line.new() as line:
                line.product_no_variant_attribute_value_ids = attribute_never.template_value_ids[0]
                line.product_id = product_template.product_variant_id
        self.assertEqual(purchase_order.order_line.name, 'matrixFR\nPA4FR: PAV41FR')
