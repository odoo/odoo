# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged, HttpCase


@tagged("post_install_l10n", "post_install", "-at_install")
class TestBrazilianAddress(HttpCase):
    def test_brazilian_address_frontend(self):
        """Test the visibility of fields and autocompletion of Brazilian state and city based on zip."""
        website = self.env["website"].get_current_website()
        website.company_id.account_fiscal_country_id = website.company_id.country_id = self.env.ref("base.br")
        self.env["product.product"].create(
            {
                "name": "Brazilian test product",
                "list_price": 12.50,
                "is_published": True,
            }
        )
        self.start_tour("/", "test_brazilian_address")
