from unittest.mock import MagicMock, patch

from freezegun import freeze_time

from odoo import Command
from odoo.tests import tagged
from odoo.tools import file_open
from odoo.addons.l10n_tr_nilvera_einvoice.tests.test_xml_ubl_tr_common import TestUBLTRCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestEdispatchUBLTr(TestUBLTRCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse_1 = cls.env['stock.warehouse'].create({
            'reception_steps': 'one_step',
            'delivery_steps': 'ship_only',
            'code': 'TRW',
            'sequence': 5,
        })
        cls.warehouse_1.out_type_id.sequence_code = "WH/NIL/"

    def test_xml_invoice_with_edispatches(self):
        with freeze_time('2025-03-05'):
            self.eidspatch_ids = self.env['stock.picking'].create([
                {
                    'partner_id': self.einvoice_partner.id,
                    'picking_type_id': self.warehouse_1.out_type_id.id,
                    'location_id': self.warehouse_1.lot_stock_id.id,
                    'move_line_ids': [
                        Command.create({'product_id': self.product_a.id, 'qty_done': qty}),
                    ],
                    'l10n_tr_nilvera_send_status': 'sent',
                } for qty in [1, 2]
            ])
            generated_xml = self._generate_invoice_xml(
                partner_id=self.einvoice_partner,
                l10n_tr_nilvera_edispatch_ids=self.eidspatch_ids.ids
            )

        with file_open('l10n_tr_nilvera_edispatch/tests/test_files/invoice_with_edispatches.xml', 'rb') as expected_xml_file:
            expected_xml = expected_xml_file.read()

        self.assertXmlTreeEqual(self.get_xml_tree_from_string(generated_xml), self.get_xml_tree_from_string(expected_xml))

    def _check_nilvera_customer_with_aliases(self, aliases, failing_document_type=None):
        """ Verify the e-Invoice partner on Nilvera, registered with `aliases`: a list of (document type, alias name).

        Like Nilvera, the taxpayer check only returns the aliases of the document type asked with
        `globalUserType`. Return the document types asked, in order.
        """
        def mock_request(method, endpoint, params, handle_response):
            document_type = params['globalUserType']
            return MagicMock(
                status_code=500 if document_type == failing_document_type else 200,
                json=lambda: [{'DocumentType': document_type, 'Name': name} for alias_type, name in aliases if alias_type == document_type],
            )

        with (
            patch('odoo.addons.l10n_tr_nilvera.lib.nilvera_client.NilveraClient.request', side_effect=mock_request) as mocked_request,
            patch.object(self.env.cr, 'commit', autospec=True),
        ):
            self.assertEqual(self.einvoice_partner._check_nilvera_customer(), not failing_document_type)
        return [call.kwargs['params']['globalUserType'] for call in mocked_request.call_args_list]

    def test_check_nilvera_customer_aliases_per_document_type(self):
        """ Each alias field must be set to an alias registered for its own document type. """
        partner = self.einvoice_partner
        requested_types = self._check_nilvera_customer_with_aliases([
            ('DespatchAdvice', 'urn:mail:dispatch@example.com'),
            ('Invoice', 'urn:mail:invoice@example.com'),
        ])
        self.assertEqual(requested_types, ['Invoice', 'DespatchAdvice'])
        self.assertEqual(partner.l10n_tr_nilvera_customer_alias_id.name, 'urn:mail:invoice@example.com')
        self.assertEqual(partner.l10n_tr_nilvera_edispatch_alias_id.name, 'urn:mail:dispatch@example.com')

        # The partner is no longer registered for e-Dispatch: its e-Dispatch alias is cleared.
        self._check_nilvera_customer_with_aliases([('Invoice', 'urn:mail:invoice@example.com')])
        self.assertEqual(partner.l10n_tr_nilvera_customer_alias_id.name, 'urn:mail:invoice@example.com')
        self.assertFalse(partner.l10n_tr_nilvera_edispatch_alias_id)

        # Nothing is changed when one of the document types can't be checked.
        self._check_nilvera_customer_with_aliases([
            ('Invoice', 'urn:mail:new_invoice@example.com'),
            ('DespatchAdvice', 'urn:mail:dispatch@example.com'),
        ], failing_document_type='DespatchAdvice')
        self.assertEqual(partner.l10n_tr_nilvera_customer_alias_ids.mapped('name'), ['urn:mail:invoice@example.com'])

    def test_check_nilvera_customer_earchive(self):
        """ The aliases of a partner not registered for e-Invoice are reset, and its other document types aren't checked. """
        self._check_nilvera_customer_with_aliases([
            ('Invoice', 'urn:mail:invoice@example.com'),
            ('DespatchAdvice', 'urn:mail:dispatch@example.com'),
        ])
        requested_types = self._check_nilvera_customer_with_aliases([('DespatchAdvice', 'urn:mail:dispatch@example.com')])
        self.assertEqual(requested_types, ['Invoice'])
        self.assertRecordValues(self.einvoice_partner, [{
            'l10n_tr_nilvera_customer_status': 'earchive',
            'l10n_tr_nilvera_customer_alias_id': False,
            'l10n_tr_nilvera_edispatch_alias_id': False,
        }])
