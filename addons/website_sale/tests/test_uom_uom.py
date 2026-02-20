from odoo.tests import tagged

from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


@tagged('post_install', '-at_install')
class TestUomUom(WebsiteSaleCommon):

    def test_uom_is_available_if_no_website_set(self):
        uom = self.env['uom.uom'].create({
            'name': 'Test UoM'
        })

        self.assertTrue(uom._is_website_available())

    def test_uom_is_available_for_current_website(self):
        uom = self.env['uom.uom'].create({
            'name': 'Test UoM',
            'website_ids': [self.website.id]
        })

        self.assertTrue(uom._is_website_available())

    def test_uom_is_not_available_with_different_website(self):
        website = self.env['website'].create({
            'name': 'Other website'
        })

        uom = self.env['uom.uom'].create({
            'name': 'Test UoM',
            'website_ids': [website.id]
        })

        self.assertFalse(uom._is_website_available())
