# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests


@odoo.tests.tagged('post_install_l10n', 'post_install', '-at_install')
class TestWebsiteSalePe(odoo.tests.HttpCase):
    def test_change_address(self):
        self.env['product.product'].create({
            'name': 'Test Product',
            'standard_price': 70.0,
            'list_price': 70.0,
            'website_published': True,
        })
        website = self.env['website'].get_current_website()
        website.company_id.account_fiscal_country_id = website.company_id.country_id = self.env.ref('base.pe')
        self.start_tour("/", 'update_the_address_for_peru_company', login="admin")
        self.assertEqual(self.env.ref('base.user_admin').partner_id.vat, False)
