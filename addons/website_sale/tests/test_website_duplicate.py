# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


@tagged('post_install', '-at_install')
class TestWebsiteSaleDuplicate(WebsiteSaleCommon):
    _test_user_groups = ('base.group_system',)

    def test_duplicate_website(self):
        barcode_field = self.env['website.sale.extra.field'].create({
            'website_id': self.website.id,
            'field_id': self.env['ir.model.fields']._get('product.template', 'barcode').id,
        })

        new_website = self.website.copy()

        def checkout_steps(website):
            steps = self.env['website.checkout.step'].search([('website_id', '=', website.id)], order='id')
            return [(step.step_href, step.is_published) for step in steps]

        self.assertEqual(checkout_steps(new_website), checkout_steps(self.website),
                         "The copy has the checkout steps of its source, published alike, and no others")
        self.assertEqual(new_website.shop_extra_field_ids.field_id, barcode_field.field_id)
        self.assertEqual(self.website.shop_extra_field_ids, barcode_field, "The source keeps its extra fields")
