import base64

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import misc

from odoo.addons.l10n_ro_edi_stock.tests.common import TestL10nRoEdiStockCommon

from unittest.mock import patch
from freezegun import freeze_time


@patch('odoo.addons.l10n_ro_edi_stock.models.etransport_api.ETransportAPI._make_etransport_request')
@tagged("post_install_l10n", "post_install", "-at_install")
class TestETransportFlows(TestL10nRoEdiStockCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.startClassPatcher(freeze_time('2025-01-14'))
        company = cls.company_data['company']

        company.write({
            'vat': '9000123456789',
            'street': 'Calea Nationala 85',
            'city': 'Botosani',
            'zip': '710052',
            'state_id': cls.env.ref('base.RO_BT').id,
            'l10n_ro_edi_access_token': 'some access token',
        })

        cls.shipping_partner = cls.env['res.partner'].create({
            'name': 'RO Shipping Partner',
            'vat': '8001011234567',
            'street': 'Strada Mihai Viteazul 22',
            'city': 'Caransebes',
            'zip': '325400',
            'state_id': cls.env.ref('base.RO_CS').id,
            'country_id': cls.env.ref('base.ro').id,
        })

        cls.customer = cls.env['res.partner'].create({
            'name': 'RO Customer',
            'vat': 'RO1234567897',
            'street': 'Strada General Traian Moșoiu 24',
            'city': 'Bran',
            'zip': '507025',
            'state_id': cls.env.ref('base.RO_BV').id,
            'country_id': cls.env.ref('base.ro').id,
        })

        cls.carrier = cls.env.ref('delivery.free_delivery_carrier')
        cls.product_a.weight = 1

        if 'intrastat_code_id' in cls.env['product.product']._fields:
            cls.default_intrastat_code = cls.env.ref('account_intrastat.commodity_code_2018_1012100')
            cls.product_a.intrastat_code_id = cls.default_intrastat_code

        cls.delivery_picking = cls.create_stock_picking(
            partner=cls.customer,
            product_data=[{
                'product_id': cls.product_a,
                'product_uom_qty': 10.0,
                'quantity': 10.0,
            }],
        )

        cls.receipt_picking = cls.create_stock_picking(
            name='receipt_picking',
            partner=cls.customer,
            picking_type=cls.warehouse.in_type_id,
            product_data=[{
                'product_id': cls.product_a,
                'product_uom_qty': 10.0,
                'quantity': 10.0,
            }],
        )

        cls.successful_upload_response = {
            'content': {
                "dateResponse": "202212231132",
                "ExecutionStatus": 0,
                "index_incarcare": 1,
                "UIT": "A0002",
                "trace_id": "96cd587e-298b-4245-ad7d-2607d973f9d4",
                "ref_declarant": "",
                "atentie": "Verificati starea XML-ului transmis. Codul UIT este valabil din momentul in care apare ca valid dupa apelul de stare",
            }
        }

    def _assert_picking_state(self, picking, state=False, amt_documents=0, enabled_fields=('enable', 'fields_readonly')):
        self.assertEqual(picking.l10n_ro_edi_stock_state, state)
        if amt_documents > 0:
            self.assertTrue(picking.l10n_ro_edi_stock_document_ids)
            self.assertEqual(len(picking.l10n_ro_edi_stock_document_ids), amt_documents)
        else:
            self.assertFalse(picking.l10n_ro_edi_stock_document_ids)

        for suffix in ('enable', 'enable_send', 'enable_fetch', 'enable_amend', 'fields_readonly'):
            field_value = getattr(picking, f'l10n_ro_edi_stock_{suffix}')
            self.assertEqual(field_value, suffix in enabled_fields)

    def _assert_etransport_document(self, document, filename):
        with misc.file_open(f'{self.test_module}/tests/test_files/{filename}.xml', 'rb') as file:
            expected_document = file.read()

        expected_tree = self.get_xml_tree_from_string(expected_document)

        if 'intrastat_code_id' in self.env['product.product']._fields:
            nsmap = expected_tree.nsmap
            nsmap['etr'] = nsmap[None]
            nsmap.pop(None)
            for tag in expected_tree.xpath('//*/etr:bunuriTransportate', namespaces=nsmap):
                tag.attrib['codTarifar'] = self.default_intrastat_code.code

        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(base64.b64decode(document.attachment)),
            expected_tree,
        )

    def test_send_and_amend_etransport(self, make_request):
        self._assert_picking_state(self.delivery_picking, enabled_fields=['enable'])

        with self.assertRaises(UserError, msg=f'The picking {self.delivery_picking.name} is missing a delivery carrier.'):
            self.delivery_picking.button_validate()

        self.delivery_picking.carrier_id = self.carrier
        with self.assertRaises(UserError, msg=f'The delivery carrier of {self.delivery_picking.name} is missing the partner field value.'):
            self.delivery_picking.button_validate()

        self.delivery_picking.carrier_id.l10n_ro_edi_stock_partner_id = self.shipping_partner
        self.delivery_picking.button_validate()
        self._assert_picking_state(self.delivery_picking, enabled_fields=['enable', 'enable_send'])

        # Add eTransport data
        self.delivery_picking.write({
            'l10n_ro_edi_stock_operation_type': '30',
            'l10n_ro_edi_stock_operation_scope': '705',
            'l10n_ro_edi_stock_vehicle_number': 'BN18CTL',
        })

        # Sending to ANAF failed
        make_request.return_value = {'error': 'some error happened'}
        self.delivery_picking.action_l10n_ro_edi_stock_send_etransport()
        self._assert_picking_state(self.delivery_picking, 'stock_sending_failed', 1, ('enable', 'enable_send'))
        self.assertTrue(self.delivery_picking.l10n_ro_edi_stock_document_ids.message == 'some error happened')

        # Successfully sent to ANAF
        make_request.return_value = self.successful_upload_response
        self.delivery_picking.action_l10n_ro_edi_stock_send_etransport()
        self._assert_picking_state(self.delivery_picking, 'stock_sent', 1, ('enable', 'enable_fetch', 'fields_readonly'))
        self._assert_etransport_document(self.delivery_picking.l10n_ro_edi_stock_document_ids, 'test_send_and_amend_etransport_1')

        # ANAF is still validating the document
        make_request.return_value = {
            'content': {
                "stare": "in prelucrare",
                "dateResponse": "202208021100",
                "ExecutionStatus": 0,
                "trace_id": "096c6b71-b7b8-42b1-b3f1-b4f5dafdce74",
            }
        }
        self.delivery_picking.action_l10n_ro_edi_stock_fetch_status()
        self._assert_picking_state(self.delivery_picking, 'stock_sent', 1, ('enable', 'enable_fetch', 'fields_readonly'))

        # Document has been successfully validated
        make_request.return_value = {
            'content': {
                "stare": "ok",
                "dateResponse": "202208021047",
                "ExecutionStatus": 0,
                "trace_id": "366efb31-57a0-42c2-9404-72bfcbba4693",
            }
        }
        self.delivery_picking.action_l10n_ro_edi_stock_fetch_status()
        self._assert_picking_state(self.delivery_picking, 'stock_validated', 1, ('enable', 'enable_amend'))

        # Add some changes to the etransport data
        self.delivery_picking.write({
            'l10n_ro_edi_stock_remarks': 'some remarks',
            'l10n_ro_edi_stock_vehicle_number': 'BM19CTK',
        })

        # Send amended changes to ANAF
        make_request.return_value = self.successful_upload_response
        self.delivery_picking.with_context(test_send_and_amend_etransport='amend').action_l10n_ro_edi_stock_send_etransport()

        self._assert_picking_state(self.delivery_picking, 'stock_sent', 2, ('enable', 'enable_fetch', 'fields_readonly'))
        self._assert_etransport_document(self.delivery_picking._l10n_ro_edi_stock_get_last_document('stock_sent'), 'test_send_and_amend_etransport_2')

        # Amended document has been successfully validated
        make_request.return_value = {
            'content': {
                "stare": "ok",
                "dateResponse": "202208021047",
                "ExecutionStatus": 0,
                "trace_id": "366efb31-57a0-42c2-9404-72bfcbba4693",
            }
        }
        self.delivery_picking.action_l10n_ro_edi_stock_fetch_status()
        self._assert_picking_state(self.delivery_picking, 'stock_validated', 2, ('enable', 'enable_amend'))
        self._assert_etransport_document(self.delivery_picking._l10n_ro_edi_stock_get_last_document('stock_validated'), 'test_send_and_amend_etransport_2')

    def test_intra_community_purchase(self, make_request):
        self.receipt_picking.carrier_id = self.carrier
        self.receipt_picking.carrier_id.l10n_ro_edi_stock_partner_id = self.shipping_partner
        self.receipt_picking.button_validate()

        # Add eTransport data
        self.receipt_picking.write({
            'l10n_ro_edi_stock_operation_type': '10',
            'l10n_ro_edi_stock_operation_scope': '201',
            'l10n_ro_edi_stock_vehicle_number': 'BN18CTL',
            'l10n_ro_edi_stock_trailer_1_number': 'B865MHO',
            'l10n_ro_edi_stock_start_loc_type': 'bcp',  # Select border crossing point as start location type
            'l10n_ro_edi_stock_start_bcp': '3',
        })

        # Successfully sent to ANAF
        make_request.return_value = self.successful_upload_response
        self.receipt_picking.action_l10n_ro_edi_stock_send_etransport()
        self._assert_picking_state(self.receipt_picking, 'stock_sent', 1, ('enable', 'enable_fetch', 'fields_readonly'))
        self._assert_etransport_document(self.receipt_picking.l10n_ro_edi_stock_document_ids, 'test_intra_community_purchase_1')

    def test_export(self, make_request):
        self.delivery_picking.carrier_id = self.carrier
        self.delivery_picking.carrier_id.l10n_ro_edi_stock_partner_id = self.shipping_partner
        self.delivery_picking.button_validate()

        self.delivery_picking.write({
            'l10n_ro_edi_stock_operation_type': '50',
            'l10n_ro_edi_stock_operation_scope': '9999',
            'l10n_ro_edi_stock_vehicle_number': 'BN18CTL',
            'l10n_ro_edi_stock_trailer_1_number': 'B865MHO',
            'l10n_ro_edi_stock_trailer_2_number': 'AB12AAA',
            'l10n_ro_edi_stock_end_loc_type': 'customs',  # Select customs office as end location type
            'l10n_ro_edi_stock_end_customs_office': '112901',
        })

        # Successfully sent to ANAF
        make_request.return_value = self.successful_upload_response
        self.delivery_picking.action_l10n_ro_edi_stock_send_etransport()
        self._assert_picking_state(self.delivery_picking, 'stock_sent', 1, ('enable', 'enable_fetch', 'fields_readonly'))
        self._assert_etransport_document(self.delivery_picking.l10n_ro_edi_stock_document_ids, 'test_export_1')
