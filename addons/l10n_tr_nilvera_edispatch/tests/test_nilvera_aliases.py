from io import BytesIO
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

    def _create_edispatch(self):
        picking_type = self.env['stock.picking.type'].search([('code', '=', 'outgoing')], limit=1)
        return self.env['stock.picking'].create({
            'partner_id': self.einvoice_partner.id,
            'picking_type_id': picking_type.id,
            'location_id': picking_type.default_location_src_id.id,
            'location_dest_id': picking_type.default_location_dest_id.id,
        })

    @patch(
        'odoo.addons.l10n_tr_nilvera.lib.nilvera_client.NilveraClient.request',
        side_effect=mock_nilvera_request(
            invoice_aliases=['urn:mail:invoice@example.com'],
            dispatch_aliases=['urn:mail:dispatch@example.com'],
        ),
    )
    def test_sync_edispatch_alias(self, mocked_request):
        """ Ensure both Invoice and DespatchAdvice aliases are synced and assigned to their respective fields. """
        with patch.object(self.env.cr, 'commit', autospec=True):
            self.einvoice_partner._check_nilvera_customer()

        self.assertEqual(self.einvoice_partner.l10n_tr_nilvera_customer_alias_id.name, 'urn:mail:invoice@example.com')
        self.assertEqual(self.einvoice_partner.l10n_tr_nilvera_edispatch_alias_id.name, 'urn:mail:dispatch@example.com')
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
                '/general/GlobalCompany/Check/TaxNumber/1729171602',
                handle_response=False,
            ),
            call(
                'GET',
                '/general/GlobalCompany/GetGlobalCustomerInfo/1729171602',
                params={'globalUserType': 'Invoice'},
                handle_response=False,
            ),
            call(
                'GET',
                '/general/GlobalCompany/GetGlobalCustomerInfo/1729171602',
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

        self.assertEqual(self.einvoice_partner.l10n_tr_nilvera_customer_alias_id.name, 'urn:mail:invoice@example.com')
        self.assertFalse(self.einvoice_partner.l10n_tr_nilvera_edispatch_alias_id)

    @patch('odoo.addons.l10n_tr_nilvera.lib.nilvera_client.NilveraClient.request')
    def test_submit_edispatch_fallback_alias(self, mocked_request):
        """
        When the recipient has no e-Dispatch alias, submission must fallback to GİB's
        official virtual mailbox alias required for e-Arşiv delivery.
        """
        mocked_request.return_value = MagicMock(status_code=200)
        picking = self._create_edispatch()
        self.assertFalse(picking.partner_id.l10n_tr_nilvera_edispatch_alias_id)

        # Dummy XML payload (submit_document streams the file without parsing its content)
        xml_file = BytesIO(b'<xml/>')
        xml_file.name = 'dispatch.xml'
        picking._l10n_tr_nilvera_submit_document(xml_file)

        mocked_request.assert_called_once_with(
            'POST',
            endpoint='/edespatch/Send/Xml',
            params={'Alias': 'urn:mail:irsaliyepk@gib.gov.tr'},
            files={'file': ('dispatch.xml', xml_file, 'application/xml')},
            handle_response=False,
        )

    def test_multi_alias_edispatch(self):
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
