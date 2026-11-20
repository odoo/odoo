from unittest.mock import MagicMock, call, patch

from odoo.tests import tagged
from odoo.addons.l10n_tr_nilvera_einvoice.tests.test_xml_ubl_tr_common import TestUBLTRCommon


def mock_nilvera_request(invoice_aliases=(), dispatch_aliases=()):
    def mock_request(method, endpoint, *args, **kwargs):
        response = MagicMock(status_code=200)
        if method == 'GET' and 'Check/TaxNumber' in endpoint:
            response.json.return_value = [{'Name': 'urn:mail:generic@example.com'}]
        elif method == 'GET' and 'GetGlobalCustomerInfo' in endpoint:
            aliases_map = {
                'Invoice': [{'Name': name} for name in invoice_aliases],
                'DespatchAdvice': [{'Name': name} for name in dispatch_aliases],
            }
            response.json.return_value = {
                'Aliases': aliases_map.get(kwargs.get('params', {}).get('globalUserType'), []),
            }
        return response
    return mock_request


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestNilveraAliases(TestUBLTRCommon):

    @patch(
        'odoo.addons.l10n_tr_nilvera.lib.nilvera_client.NilveraClient.request',
        side_effect=mock_nilvera_request(
            invoice_aliases=['urn:mail:invoice@example.com'],
            dispatch_aliases=['urn:mail:dispatch@example.com'],
        ),
    )
    def test_sync_customer_aliases_segregation(self, mocked_request):
        """ Ensure both Invoice and DespatchAdvice aliases are synced and assigned to their respective fields. """
        with patch.object(self.env.cr, 'commit', autospec=True):
            self.einvoice_partner._check_nilvera_customer()

        self.assertEqual(
            self.einvoice_partner.l10n_tr_nilvera_customer_alias_id.name,
            'urn:mail:invoice@example.com',
        )
        self.assertEqual(
            self.einvoice_partner.l10n_tr_nilvera_edispatch_alias_id.name,
            'urn:mail:dispatch@example.com',
        )
        self.assertNotEqual(
            self.einvoice_partner.l10n_tr_nilvera_customer_alias_id,
            self.einvoice_partner.l10n_tr_nilvera_edispatch_alias_id,
        )
        self.assertSetEqual(
            set(self.einvoice_partner.l10n_tr_nilvera_customer_alias_ids.mapped('global_user_type')),
            {'Invoice', 'DespatchAdvice'},
        )
        mocked_request.assert_has_calls([
            call(
                'GET',
                f'/general/GlobalCompany/Check/TaxNumber/{self.einvoice_partner.vat}',
                handle_response=False,
            ),
            call(
                'GET',
                f'/general/GlobalCompany/GetGlobalCustomerInfo/{self.einvoice_partner.vat}',
                params={'globalUserType': 'Invoice'},
                handle_response=False,
            ),
            call(
                'GET',
                f'/general/GlobalCompany/GetGlobalCustomerInfo/{self.einvoice_partner.vat}',
                params={'globalUserType': 'DespatchAdvice'},
                handle_response=False,
            ),
        ])
        self.assertEqual(mocked_request.call_count, 3)

    @patch(
        'odoo.addons.l10n_tr_nilvera.lib.nilvera_client.NilveraClient.request',
        side_effect=mock_nilvera_request(invoice_aliases=['urn:mail:invoice@example.com']),
    )
    def test_sync_alias_separation_invoice_only(self, mocked_request):
        """ A partner registered only for e-Invoice must not receive an e-Dispatch alias. """
        with patch.object(self.env.cr, 'commit', autospec=True):
            self.einvoice_partner._check_nilvera_customer()

        self.assertEqual(
            self.einvoice_partner.l10n_tr_nilvera_customer_alias_id.name,
            'urn:mail:invoice@example.com',
        )
        self.assertFalse(self.einvoice_partner.l10n_tr_nilvera_edispatch_alias_id)

    def test_multi_alias_scoped_per_document_type(self):
        """
        Ensure multi-alias detection is scoped per document type.
        Having 1 Invoice alias + 1 DespatchAdvice alias is standard and must not trigger
        a warning; multiple aliases for the same document type must trigger the warning.
        """
        alias_model = self.env['l10n_tr.nilvera.alias']
        # 1 invoice + 1 dispatch alias should not be considered multi-alias
        alias_model.create([
            {
                'name': 'urn:mail:invoice@example.com',
                'partner_id': self.einvoice_partner.id,
                'global_user_type': 'Invoice',
            },
            {
                'name': 'urn:mail:dispatch1@example.com',
                'partner_id': self.einvoice_partner.id,
                'global_user_type': 'DespatchAdvice',
            },
        ])
        self.assertFalse(self.einvoice_partner._l10n_tr_nilvera_has_multiple_aliases())

        # Adding a second dispatch alias should trigger multi-alias
        alias_model.create({
            'name': 'urn:mail:dispatch2@example.com',
            'partner_id': self.einvoice_partner.id,
            'global_user_type': 'DespatchAdvice',
        })
        self.assertTrue(self.einvoice_partner._l10n_tr_nilvera_has_multiple_aliases())

    @patch('odoo.addons.l10n_tr_nilvera.lib.nilvera_client.NilveraClient.request')
    def test_earchive_does_not_sync_aliases(self, mocked_request):
        """ Ensure non-eInvoice taxpayers do not query document aliases. """
        response = MagicMock(status_code=200)
        response.json.return_value = []
        mocked_request.return_value = response

        with patch.object(self.env.cr, 'commit', autospec=True):
            self.assertTrue(self.earchive_partner._check_nilvera_customer())

        self.assertEqual(self.earchive_partner.l10n_tr_nilvera_customer_status, 'earchive')
        self.assertFalse(self.earchive_partner.l10n_tr_nilvera_customer_alias_id)
        self.assertFalse(self.earchive_partner.l10n_tr_nilvera_edispatch_alias_id)
        mocked_request.assert_called_once_with(
            'GET',
            f'/general/GlobalCompany/Check/TaxNumber/{self.earchive_partner.vat}',
            handle_response=False,
        )

    @patch('odoo.addons.l10n_tr_nilvera.lib.nilvera_client.NilveraClient.request')
    def test_sync_aliases_removes_missing_aliases(self, mocked_request):
        """ Ensure aliases removed on Nilvera are unlinked in Odoo. """
        self.env['l10n_tr.nilvera.alias'].create([
            {
                'name': 'urn:mail:old_invoice@example.com',
                'partner_id': self.einvoice_partner.id,
                'global_user_type': 'Invoice',
            },
            {
                'name': 'urn:mail:old_dispatch@example.com',
                'partner_id': self.einvoice_partner.id,
                'global_user_type': 'DespatchAdvice',
            },
        ])
        self.assertEqual(len(self.einvoice_partner.l10n_tr_nilvera_customer_alias_ids), 2)

        response = MagicMock(status_code=200)
        response.json.return_value = {'Aliases': []}
        mocked_request.side_effect = lambda *args, **kwargs: response

        with patch.object(self.env.cr, 'commit', autospec=True):
            self.assertTrue(self.einvoice_partner._l10n_tr_nilvera_sync_customer_aliases('Invoice'))

        invoice_aliases = self.einvoice_partner.l10n_tr_nilvera_customer_alias_ids.filtered(
            lambda alias: alias.global_user_type == 'Invoice'
        )
        dispatch_aliases = self.einvoice_partner.l10n_tr_nilvera_customer_alias_ids.filtered(
            lambda alias: alias.global_user_type == 'DespatchAdvice'
        )
        self.assertFalse(invoice_aliases)
        self.assertEqual(len(dispatch_aliases), 1)

    @patch('odoo.addons.l10n_tr_nilvera.lib.nilvera_client.NilveraClient.request')
    def test_sync_alias_failure_preserves_existing_aliases(self, mocked_request):
        """ Ensure API failure during alias sync preserves existing aliases and aborts commit. """
        self.env['l10n_tr.nilvera.alias'].create({
            'name': 'urn:mail:existing_invoice@example.com',
            'partner_id': self.einvoice_partner.id,
            'global_user_type': 'Invoice',
        })
        taxpayer_response = MagicMock(status_code=200)
        taxpayer_response.json.return_value = [{'Name': 'urn:mail:existing_invoice@example.com'}]
        aliases_response = MagicMock(status_code=500)
        mocked_request.side_effect = [taxpayer_response, aliases_response]

        with patch.object(self.env.cr, 'commit', autospec=True) as mock_commit:
            self.assertFalse(self.einvoice_partner._check_nilvera_customer())
            mock_commit.assert_not_called()

        self.assertEqual(
            self.einvoice_partner.l10n_tr_nilvera_customer_alias_id.name,
            'urn:mail:existing_invoice@example.com',
        )
