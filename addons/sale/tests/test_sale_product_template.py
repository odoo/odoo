# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo.tests import tagged, users

from odoo.addons.sale.tests.common import SaleCommon


@tagged('post_install', '-at_install')
class TestSaleProductTemplate(SaleCommon):

    @users('salesman')
    def test_sale_get_configurator_display_price(self):
        configurator_price = self.env['product.template']._get_configurator_display_price(
            product_or_template=self._create_product(list_price=40),
            quantity=3,
            date=datetime(2000, 1, 1),
            currency=self.currency,
            pricelist=self.pricelist,
        )

        self.assertEqual(configurator_price[0], 40)

    @users('salesman')
    def test_sale_get_additional_configurator_data(self):
        configurator_data = self.env['product.template']._get_additional_configurator_data(
            product_or_template=self.product,
            date=datetime(2000, 1, 1),
            currency=self.currency,
            pricelist=self.pricelist,
        )

        self.assertEqual(configurator_data, {})

    def test_restrict_optional_product_on_same_product_template(self):
        """Test that a product template cannot be added as an optional product on itself."""
        product_template = self.product.product_tmpl_id
        product_template.optional_product_ids = product_template
        self.env.invalidate_all()
        self.assertEqual(product_template.optional_product_ids, self.env["product.template"])
