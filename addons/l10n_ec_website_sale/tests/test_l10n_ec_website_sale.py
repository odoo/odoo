# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import HttpCase, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUi(HttpCase, AccountTestInvoicingCommon):

    def test_checkout_address_ec(self):
        self.env.company.country_id = self.env.ref('base.ec').id
        self.env.ref('base.user_admin').write({
            'company_id': self.env.company.id,
            'company_ids': [(4, self.env.company.id)],
        })
        self.env['product.product'].create({
            'name': 'Test Product',
            'sale_ok': True,
            'website_published': True,
        })
        self.env['ir.config_parameter'].set_param('sale.automatic_invoice', True)
        self.env['website'].get_current_website().company_id = self.env.company.id
        user_admin = self.env.ref('base.user_admin')
        user_admin.company_ids = user_admin.company_ids + self.env.company
        self.start_tour('/shop', 'shop_checkout_address_ec', login='admin')

    def test_new_billing_ec(self):
        self.env.company.country_id = self.env.ref('base.ec').id
        self.env.ref('base.user_admin').write({
            'company_id': self.env.company.id,
            'company_ids': [(4, self.env.company.id)],
        })
        # Avoid Shipping/Billing address page
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
        self.env['product.product'].create({
            'name': 'Test Product',
            'sale_ok': True,
            'website_published': True,
        })
        self.env['ir.config_parameter'].set_param('sale.automatic_invoice', True)
        self.env['website'].get_current_website().company_id = self.env.company.id
        user_admin = self.env.ref('base.user_admin')
        user_admin.company_ids = user_admin.company_ids + self.env.company
        self.start_tour('/shop', 'tour_new_billing_ec', login='admin')
