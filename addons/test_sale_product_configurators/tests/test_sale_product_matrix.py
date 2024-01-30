# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo.tests import tagged, loaded_demo_data

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.product_matrix.tests.common import TestMatrixCommon

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install')
class TestSaleMatrixUi(TestMatrixCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Adding sale users to test the access rights
        mail_new_test_user(
            cls.env,
            name='Salesman',
            login='salesman',
            password='salesman',
            groups='sales_team.group_sale_salesman',
        )

        # Setup partner since user salesman don't have the right to create it on the fly
        cls.env['res.partner'].create({'name': 'Agrolait'})

        # Setup currency
        cls.env['res.currency'].search([('name', '!=', 'USD')]).with_context(force_deactivate=True).action_archive()
        cls.currency = cls.env['res.currency'].search([('name', '=', 'USD')])
        cls.currency.action_unarchive()

    def test_sale_matrix_ui(self):
        # TODO: Adapt to work without demo data
        if not loaded_demo_data(self.env):
            _logger.warning("This test relies on demo data. To be rewritten independently of demo data for accurate and reliable results.")
            return

        # Set the template as configurable by matrix.
        self.matrix_template.product_add_mode = "matrix"

        self.start_tour("/web", 'sale_matrix_tour', login='salesman')

        # Ensures some dynamic create variants have been created by the matrix
        # Ensures a SO has been created with exactly x lines ...

        self.assertEqual(len(self.matrix_template.product_variant_ids), 8)
        self.assertEqual(len(self.matrix_template.product_variant_ids.product_template_attribute_value_ids), 6)
        self.assertEqual(len(self.matrix_template.attribute_line_ids.product_template_value_ids), 8)
        self.env['sale.order.line'].search([('product_id', 'in', self.matrix_template.product_variant_ids.ids)]).order_id.action_confirm()

        self.env.flush_all()
        self.assertEqual(round(self.matrix_template.sales_count, 2), 56.8)
        for variant in self.matrix_template.product_variant_ids:
            # 5 and 9.2 because of no variant attributes
            self.assertIn(round(variant.sales_count, 2), [5, 9.2])

        # Ensure no duplicate line has been created on the SO.
        # NB: the *2 is because the no_variant attribute doesn't create a variant
        # but still gives different order lines.
        self.assertEqual(
            len(self.env['sale.order.line'].search([('product_id', 'in', self.matrix_template.product_variant_ids.ids)])),
            len(self.matrix_template.product_variant_ids)*2
        )
