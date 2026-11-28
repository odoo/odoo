from unittest.mock import patch

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged
from odoo.tools import mute_logger

IAP_JSONRPC = 'odoo.addons.l10n_dk_mitid.models.res_company.iap_tools.iap_jsonrpc'


@tagged('post_install', '-at_install')
class TestResCompanyCVR(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_info = {
            'cvr': '12345674',
            'name': 'Testorganisation nr. 12345674',
            'status': 'aktiv',
            'address': {
                'street': 'Vesterbrogade 12, 2, tv',
                'street2': 'c/o Odoo',
                'zip': '1620',
                'city': 'København V',
                'country_code': 'DK',
            },
            'email': 'info@example.com',
            'phone': '12345678',
        }

    def _create_company(self, **values):
        return self.env['res.company'].create({'name': f"My Company {self.env['res.company'].search_count([])}", **values})

    def test_autofill_from_cvr(self):
        company = self._create_company(company_registry='12345674', city='Aarhus')
        company_name = company.name

        with patch(IAP_JSONRPC, return_value=self.company_info) as mock_iap:
            company._mitid_autofill_from_cvr()

        self.assertEqual(mock_iap.call_args.kwargs['params'], {'cvr': '12345674'})
        self.assertRecordValues(company, [{
            # What the user has filled in is kept
            'name': company_name,
            'city': 'Aarhus',
            'vat': 'DK12345674',
            'street': 'Vesterbrogade 12, 2, tv',
            'street2': 'c/o Odoo',
            'zip': '1620',
            'country_id': self.env.ref('base.dk').id,
            'email': 'info@example.com',
            'phone': '12345678',
        }])

    def test_autofill_from_cvr_not_applicable(self):
        companies = self._create_company() + self._create_company(company_registry='90004317', country_id=self.env.ref('base.be').id)

        with patch(IAP_JSONRPC) as mock_iap:
            companies._mitid_autofill_from_cvr()

        mock_iap.assert_not_called()

    def test_autofill_from_cvr_errors(self):
        company = self._create_company(company_registry='90004317')

        # The IAP route returns an error (e.g. unknown CVR)
        with patch(IAP_JSONRPC, return_value={'status': 'fail', 'error': 'No company found', 'code': 104}):
            company._mitid_autofill_from_cvr()
        self.assertFalse(company.street)

        # IAP can't be reached, the company is kept as it is
        with patch(IAP_JSONRPC, side_effect=AccessError("The url that this service requested returned an error.")), \
                mute_logger('odoo.addons.l10n_dk_mitid.models.res_company'):
            company._mitid_autofill_from_cvr()
        self.assertFalse(company.street)

    def test_autofill_from_cvr_invalid_vat(self):
        # The CVR numbers of the test organisations are not valid VAT numbers, the other fields are still filled in
        company = self._create_company(company_registry='90004317')

        with patch(IAP_JSONRPC, return_value={**self.company_info, 'cvr': '90004317'}):
            company._mitid_autofill_from_cvr()

        self.assertFalse(company.vat)
        self.assertEqual(company.street, 'Vesterbrogade 12, 2, tv')
