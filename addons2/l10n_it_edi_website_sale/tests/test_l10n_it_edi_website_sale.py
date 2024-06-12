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

    def test_checkout_address(self):
        # set current company's fiscal country to italy
        website = self.env['website'].get_current_website()
        website.company_id.account_fiscal_country_id = website.company_id.country_id = self.env.ref('base.it')
        self.start_tour("/", 'shop_checkout_address')
