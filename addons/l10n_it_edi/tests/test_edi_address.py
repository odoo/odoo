from odoo.tests import tagged

from odoo.addons.base.tests.common import HttpCaseWithUserPortal
from odoo.addons.l10n_it_edi.tests.common import TestItEdi


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUi(HttpCaseWithUserPortal, TestItEdi):
    def test_portal_user_codice_fiscale(self):
        self.env.company.country_id = self.env.ref('base.it')
        it_user_portal = self._create_new_portal_user(name='IT User')
        # If website is installed, the website's company (main_company) should also have country as Italy
        company = self.env.ref('base.main_company')
        company.account_fiscal_country_id = company.country_id = self.env.company.country_id

        self.start_tour("/my", 'portal_compute_codice_fiscale', login="portal_user")
        self.assertEqual(
            it_user_portal.l10n_it_codice_fiscale,
            '12345670017',
            "The user should have the Codice Fiscale filled according to the VAT",
        )
