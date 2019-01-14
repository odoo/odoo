# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests


@odoo.tests.tagged('-at_install', 'post_install')
class TestWebsiteSaleComparison(odoo.tests.TransactionCase):
    def test_01_website_sale_comparison_remove(self):
        """ This tour makes sure the product page still works after the module
        `website_sale_comparison` has been removed.

        Technically it tests the removal of copied views by the base method
        `_remove_copied_views`. The problematic view that has to be removed is
        `product_add_to_compare` because it has a reference to `add_to_compare`.
        """

        Website0 = self.env['website'].with_context(website_id=None)
        Website1 = self.env['website'].with_context(website_id=1)

        # Create a generic inherited view, with a key not starting with
        # `website_sale_comparison` otherwise the unlink will work just based on
        # the key, but we want to test also for `MODULE_UNINSTALL_FLAG`.
        product_add_to_compare = Website0.viewref('website_sale_comparison.product_add_to_compare')
        test_view_key = 'my_test.my_key'
        self.env['ir.ui.view'].with_context(website_id=None).create({
            'name': 'test inherited view',
            'key': test_view_key,
            'inherit_id': product_add_to_compare.id,
            'arch': '<div/>',
        })

        # Retrieve the generic view
        product = Website0.viewref('website_sale.product')
        # Trigger COW to create specific views of the whole tree
        product.with_context(website_id=1).write({'name': 'Trigger COW'})

        # Verify initial state: the specific views exist
        self.assertEquals(Website1.viewref('website_sale.product').website_id.id, 1)
        self.assertEquals(Website1.viewref('website_sale_comparison.product_add_to_compare').website_id.id, 1)
        self.assertEquals(Website1.viewref(test_view_key).website_id.id, 1)

        # Remove the module (use `module_uninstall` because it is enough to test
        # what we want here, no need/can't use `button_immediate_uninstall`
        # because it would commit the test transaction)
        website_sale_comparison = self.env['ir.module.module'].search([('name', '=', 'website_sale_comparison')])
        website_sale_comparison.module_uninstall()

        # Check that the generic view is correctly removed
        self.assertFalse(Website0.viewref('website_sale_comparison.product_add_to_compare', raise_if_not_found=False))
        # Check that the specific view is correctly removed
        self.assertFalse(Website1.viewref('website_sale_comparison.product_add_to_compare', raise_if_not_found=False))

        # Check that the generic inherited view is correctly removed
        self.assertFalse(Website0.viewref(test_view_key, raise_if_not_found=False))
        # Check that the specific inherited view is correctly removed
        self.assertFalse(Website1.viewref(test_view_key, raise_if_not_found=False))
