# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo.addons.product_matrix.tests.common import TestMatrixCommon


@odoo.tests.tagged('post_install', '-at_install')
class TestPurchaseMatrixUi(TestMatrixCommon):

    def test_purchase_matrix_ui(self):
        self.start_tour("/web", 'purchase_matrix_tour', login="admin")

        # Ensures some dynamic create variants have been created by the matrix
        # Ensures a SO has been created with exactly x lines ...

        self.assertEquals(len(self.matrix_template.product_variant_ids), 8)
        self.assertEquals(len(self.matrix_template.product_variant_ids.product_template_attribute_value_ids), 6)
        self.assertEquals(len(self.matrix_template.attribute_line_ids.product_template_value_ids), 8)
        self.env['purchase.order.line'].search([('product_id', 'in', self.matrix_template.product_variant_ids.ids)]).order_id.button_confirm()

        self.matrix_template.flush()
        self.assertEquals(round(self.matrix_template.purchased_product_qty, 2), 56.8)
        for variant in self.matrix_template.product_variant_ids:
            # 5 and 9.2 because of no variant attributes
            self.assertIn(round(variant.purchased_product_qty, 2), [5, 9.2])

        # Ensure no duplicate line has been created on the SO.
        # NB: the *2 is because the no_variant attribute doesn't create a variant
        # but still gives different order lines.
        self.assertEquals(
            len(self.env['purchase.order.line'].search([('product_id', 'in', self.matrix_template.product_variant_ids.ids)])),
            len(self.matrix_template.product_variant_ids)*2
        )
