from odoo.addons.base.tests.common import HttpCaseWithUserPortal
from odoo.tests import tagged


@tagged('post_install_l10n', '-at_install', 'post_install')
class TestL10nSaEdiPortalAddress(HttpCaseWithUserPortal):

    def test_address_form_identification_schemes(self):
        """The address form must render the Saudi identification schemes."""
        saudi_arabia = self.env.ref('base.sa')
        self.env.company.write({
            'country_id': saudi_arabia.id,
            'account_fiscal_country_id': saudi_arabia.id,
        })
        self.authenticate('portal', 'portal')

        response = self.url_open('/my/address?address_type=billing')

        self.assertEqual(response.status_code, 200)
        self.assertIn('l10n_sa_edi_additional_identification_scheme', response.text)
        self.assertIn('Commercial Registration Number', response.text)
