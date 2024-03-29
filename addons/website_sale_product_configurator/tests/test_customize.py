# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import HttpCase
from odoo.addons.sale_product_configurator.tests.common import TestProductConfiguratorCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestUi(HttpCase, TestProductConfiguratorCommon):

    def test_01_admin_shop_custom_attribute_value_tour(self):
        # Ensure that no pricelist is available during the test.
        # This ensures that tours which triggers on the amounts will run properly.
        self.env['product.pricelist'].search([]).action_archive()
        self.start_tour("/", 'a_shop_custom_attribute_value', login="admin")
