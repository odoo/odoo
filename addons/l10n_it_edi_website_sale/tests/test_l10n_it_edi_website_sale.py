from odoo.tests.common import HttpCase, tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUi(HttpCase):
    def setUp(self):
        super(TestUi, self).setUp()
        self.env['product.product'].create({
            'name': 'Storage Box',
            'standard_price': 70.0,
            'list_price': 79.0,
            'website_published': True,
        })
        # set current company's fiscal country to italy
        company = self.env['website'].get_current_website().company_id
        company.account_fiscal_country_id = company.country_id = self.env.ref('base.it')

    def test_checkout_address(self):
        self.start_tour("/", 'shop_checkout_address')

    def test_public_user_codice_fiscale(self):
        self.start_tour('/shop', 'shop_checkout_address_create_partner')
        new_partner = self.env['res.partner'].search([('name', '=', 'abc')])
        self.assertEqual(
            new_partner.l10n_it_codice_fiscale,
            '12345670017',
            "The new partner should have the Codice Fiscale filled according to the VAT",
        )
