# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import HttpCase
from odoo.addons.sale_product_configurator.tests.common import TestProductConfiguratorCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestUi(HttpCase, TestProductConfiguratorCommon):

    def test_01_admin_shop_custom_attribute_value_tour(self):
<<<<<<< HEAD
        # Ensure that no pricelist is available during the test.
        # This ensures that tours which triggers on the amounts will run properly.
        self.env['product.pricelist'].search([]).action_archive()
||||||| parent of 7c08ab9d16ad (temp)
        # Ensure that only one pricelist is available during the test, with the company currency.
        # This ensures that tours with triggers on the amounts will run properly.
        # To this purpose, we will ensure that only the public_pricelist is available for the default_website.
        public_pricelist = self.env.ref('product.list0')
        default_website = self.env.ref('website.default_website')
        self.env['product.pricelist'].search([
            ('id', '!=', public_pricelist.id),
            ('website_id', 'in', [False, default_website.id])]
        ).website_id = self.env.ref('website.website2')
        public_pricelist.currency_id = self.env.company.currency_id
        self._create_pricelist(public_pricelist)
=======
        # Ensure that only one pricelist is available during the test, with the company currency.
        # This ensures that tours with triggers on the amounts will run properly.
        # To this purpose, we will ensure that only the public_pricelist is available for the default_website.
        public_pricelist = self.env.ref('product.list0')
        default_website = self.env.ref('website.default_website')
        website_2 = self.env.ref('website.website2', raise_if_not_found=False)
        if not website_2:
            website_2 = self.env['website'].create({
                'name': 'My Website 2',
                'domain': '',
                'sequence': 20,
            })
        self.env['product.pricelist'].search([
            ('id', '!=', public_pricelist.id),
            ('website_id', 'in', [False, default_website.id])]
        ).website_id = website_2
        public_pricelist.currency_id = self.env.company.currency_id
        self._create_pricelist(public_pricelist)
>>>>>>> 7c08ab9d16ad (temp)
        self.start_tour("/", 'a_shop_custom_attribute_value', login="admin")
