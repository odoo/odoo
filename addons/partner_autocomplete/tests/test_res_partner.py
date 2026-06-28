from odoo.tests import common, tagged
from odoo.addons.partner_autocomplete.tests.common import MockIAPPartnerAutocomplete


@tagged('post_install', '-at_install')
class TestResPartner(common.TransactionCase, MockIAPPartnerAutocomplete):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._init_mock_partner_autocomplete()

    def test_autocomplete_fill_additional_ids_duns(self):
        """
        Ensure the DUNS number is given in multi-ids field
        """
        company = self.env['res.company'].create({'name': 'Test company 2', 'email': 'test@odoo.com'})
        target_duns = '123456789'
        with self.mockPartnerAutocomplete(default_data={'duns': target_duns}):
            res = company._enrich()
            self.assertTrue(res)

        self.assertTrue(company.additional_identifiers)
        self.assertEqual(company.additional_identifiers.get('DUNS'), target_duns)
