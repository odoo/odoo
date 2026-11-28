from unittest.mock import patch

from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, tagged
from odoo.tools import mute_logger

IAP_JSONRPC = 'odoo.addons.iap.tools.iap_tools.iap_jsonrpc'


@tagged('post_install', '-at_install')
class TestNemhandelRegistrationCVR(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['ir.config_parameter'].sudo().set_param('l10n_dk_nemhandel.edi.mode', 'prod')
        cls.company = cls.env['res.company'].create({
            'name': "Odoo Danmark ApS",
            'company_registry': '12345674',
            'vat': 'DK 12345674',
            'street': 'Vesterbrogade 12, 2, tv',
            'zip': '1620',
            'city': 'København V',
            'country_id': cls.env.ref('base.dk').id,
        })
        cls.company_info = {
            'cvr': '12345674',
            'name': 'ODOO DANMARK ApS',
            'status': 'NORMAL',
            'address': {
                'street': 'Vesterbrogade  12, 2, tv',
                'street2': '',
                'zip': '1620',
                'city': 'København V',
                'country_code': 'DK',
            },
            'email': 'info@example.com',
            'phone': '12345678',
        }

    def _create_wizard(self):
        return self.env['nemhandel.registration'].create({
            'company_id': self.company.id,
            'contact_email': 'info@example.com',
            'identifier_type': '0184',
            'identifier_value': '12345674',
        })

    def _patch_iap(self, company_info):
        def iap_jsonrpc(url, params=None, **kwargs):
            if url.endswith('/company_info'):
                if isinstance(company_info, Exception):
                    raise company_info
                return company_info
            if url.endswith('/api/id_authentication/1/authentication'):
                return {'object_uuid': 'abc', 'url_hash': 'hash'}
            raise AssertionError(f"Unexpected IAP call: {url}")
        return patch(IAP_JSONRPC, side_effect=iap_jsonrpc)

    def _assert_authentication_started(self, action, wizard):
        self.assertEqual(action['type'], 'ir.actions.act_url')
        self.assertFalse(wizard.mitid_company_differences)
        self.assertEqual(wizard.mitid_kyc_status, 'processing')

    def test_company_matches_cvr(self):
        # The case, the spaces and the CVR values missing (street2) are not differences
        wizard = self._create_wizard()
        with self._patch_iap(self.company_info):
            action = wizard.button_trigger_authentication()
        self._assert_authentication_started(action, wizard)

    def test_company_differs_from_cvr(self):
        self.company.write({'name': "My Company", 'city': 'Aarhus', 'vat': False})
        wizard = self._create_wizard()

        with self._patch_iap(self.company_info) as mock_iap:
            action = wizard.button_trigger_authentication()

        # The authentication is stopped, the differences are proposed to the user
        self.assertEqual(mock_iap.call_count, 1)
        self.assertEqual(action['res_model'], 'nemhandel.registration')
        self.assertFalse(wizard.mitid_kyc_status)
        self.assertEqual(
            [(difference['field'], difference['current_value'], difference['cvr_value']) for difference in wizard.mitid_company_differences],
            [
                ('name', "My Company", 'ODOO DANMARK ApS'),
                ('vat', '', 'DK12345674'),
                ('city', 'Aarhus', 'København V'),
            ],
        )
        self.assertIn('Aarhus', wizard.mitid_company_differences_html)

        with self._patch_iap(self.company_info):
            action = wizard.button_mitid_update_company()

        self.assertRecordValues(self.company, [{'name': 'ODOO DANMARK ApS', 'city': 'København V', 'vat': 'DK12345674'}])
        self._assert_authentication_started(action, wizard)

    def test_company_differs_from_cvr_discard(self):
        self.company.city = 'Aarhus'
        wizard = self._create_wizard()
        with self._patch_iap(self.company_info):
            wizard.button_trigger_authentication()
        self.assertTrue(wizard.mitid_company_differences)

        wizard.button_mitid_discard_company_differences()

        self.assertFalse(wizard.mitid_company_differences)
        self.assertEqual(self.company.city, 'Aarhus')
        self.assertFalse(wizard.mitid_kyc_status)

    def test_company_differences_invalid_vat(self):
        # The test CVR numbers are not valid VAT numbers, they can't be proposed
        differences = self.company._mitid_get_company_differences({**self.company_info, 'cvr': '90004317'})
        self.assertNotIn('vat', [difference['field'] for difference in differences])

    def test_company_not_in_cvr(self):
        not_found = {'status': 'fail', 'error': "No company found for the CVR number 12345674.", 'code': 104}
        wizard = self._create_wizard()

        with self._patch_iap(not_found), self.assertRaisesRegex(UserError, "No company found"):
            wizard.button_trigger_authentication()

        # The test companies are not in the CVR register
        self.env['ir.config_parameter'].sudo().set_param('l10n_dk_nemhandel.edi.mode', 'test')
        wizard = self._create_wizard()
        with self._patch_iap(not_found):
            action = wizard.button_trigger_authentication()
        self._assert_authentication_started(action, wizard)

    def test_cvr_register_unavailable(self):
        wizard = self._create_wizard()
        with self._patch_iap({'status': 'fail', 'error': "Missing credential.", 'code': 103}):
            action = wizard.button_trigger_authentication()
        self._assert_authentication_started(action, wizard)

        wizard = self._create_wizard()
        with self._patch_iap(AccessError("The url that this service requested returned an error.")), \
                mute_logger('odoo.addons.l10n_dk_mitid.wizard.nemhandel_registration'):
            action = wizard.button_trigger_authentication()
        self._assert_authentication_started(action, wizard)

    def test_company_without_cvr(self):
        self.company.company_registry = False
        wizard = self._create_wizard()
        with self._patch_iap(self.company_info) as mock_iap, self.assertRaisesRegex(UserError, "CVR number"):
            wizard.button_trigger_authentication()
        mock_iap.assert_not_called()
