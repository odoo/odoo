# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestWebsiteSalePe(HttpCase):

    def test_change_address(self):
        if self.env['ir.module.module']._get('payment_custom').state != 'installed':
            self.skipTest("Transfer provider is not installed")

        transfer_provider = self.env.ref('payment.payment_provider_transfer')
        transfer_provider.write({
            'state': 'enabled',
            'is_published': True,
        })
        transfer_provider._transfer_ensure_pending_msg_is_set()
        self.env['product.product'].create({
            'name': 'Test Product',
            'standard_price': 70.0,
            'list_price': 70.0,
            'website_published': True,
        })
        # Avoid Shipping/Billing address page (Needed when test is run without demo data)
        country_us_id = self.env['ir.model.data']._xmlid_to_res_id('base.us')
        country_us_state_id = self.env['ir.model.data']._xmlid_to_res_id('base.state_us_39')
        self.env.ref('base.partner_admin').write({
            'street': '215 Vine St',
            'city': 'Scranton',
            'zip': '18503',
            'country_id': country_us_id,
            'state_id': country_us_state_id,
            'phone': '+1 555-555-5555',
            'email': 'admin@yourcompany.example.com',
        })
        country_peru = self.env.ref('base.pe')
        self.env.company.account_fiscal_country_id = country_peru
        self.env.company.country_id = country_peru
        self.env['website'].get_current_website().company_id = self.env.company.id
        self.start_tour("/", 'update_the_address_for_peru_company', login="admin", watch=True)
