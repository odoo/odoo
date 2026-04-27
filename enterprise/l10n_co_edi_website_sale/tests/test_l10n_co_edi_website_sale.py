from odoo.tests.common import HttpCase, tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUi(HttpCase):
    def setUp(self):
        super().setUp()
        self.env['product.product'].create({
            'name': 'Test Product',
            'standard_price': 70.0,
            'list_price': 79.0,
            'website_published': True,
        })
        # set current company's fiscal country to Colombia
        website = self.env['website'].get_current_website()
        website.company_id.account_fiscal_country_id = website.company_id.country_id = self.env.ref('base.co')

    def test_checkout_set_id_nit(self):
        self.start_tour("/shop", "test_checkout_id_nit")

    def test_checkout_set_other_id(self):
        self.start_tour("/shop", "test_checkout_other_id")
