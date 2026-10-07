from odoo import fields
from odoo.tests import tagged
from odoo.tools import file_open

from odoo.addons.l10n_tr_edi_stock.tests.common import TestL10nTrEdiStockCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nTrEdiStockImport(TestL10nTrEdiStockCommon):

    def test_received_dispatch_without_provider_has_no_document(self):
        self.env.company.l10n_tr_edi_provider = False
        with file_open('l10n_tr_edi_stock/tests/test_files/test_ereceipt.xml', 'rb') as f:
            ereceipt_xml = self.env['ir.attachment'].create({'name': 'test_ereceipt_upload.xml', 'raw': f.read()})

        picking, _files_with_errors = self.env['stock.picking']._l10n_tr_create_receipts_from_attachment(ereceipt_xml)
        # Nobody holds a received e-Dispatch without a provider: there is nothing to follow up.
        self.assertFalse(picking.l10n_tr_edi_document_ids)

    def test_ereceipt_xml_without_errors_upload(self):
        with file_open('l10n_tr_edi_stock/tests/test_files/test_ereceipt.xml', 'rb') as f:
            ereceipt_xml = self.env['ir.attachment'].create({
                'name': 'test_ereceipt_upload.xml',
                'type': 'binary',
                'raw': f.read(),
            })

        picking, files_with_errors = self.env['stock.picking']._l10n_tr_create_receipts_from_attachment(ereceipt_xml)
        self.assertEqual(bool(picking), True)
        self.assertEqual(files_with_errors, [])

        warehouse_id = self.env.user._get_default_warehouse_id()

        self.assertRecordValues(
            picking,
            [{
                'partner_id': self.receipt_partner.id,
                'picking_type_id': warehouse_id.in_type_id.id,
                'location_dest_id': warehouse_id.lot_stock_id.id,
                'scheduled_date': fields.Datetime.from_string('2025-07-29 11:30:00'),
                'origin': 'EIT2025000000009',
            }],
        )
        self.assertRecordValues(
            picking.move_ids,
            [
                {
                    'product_uom_qty': quantity,
                    'uom_id': uom,
                    'location_id': self.supplier_location.id,
                    'location_dest_id': warehouse_id.lot_stock_id.id,
                }
                for quantity, uom in [(1.0, self.uom_unit), (3.0, self.uom_kgm), (4.0, self.uom_grm)]
            ],
        )
        self.assertRecordValues(
            picking.l10n_tr_edi_seller_supplier_id,
            [{
                'name': 'Test Seller',
                'country_id': self.tr_country_id,
                'vat': '1234567800',
                'zip': '62800',
            }],
        )
        self.assertRecordValues(
            picking.l10n_tr_edi_buyer_id,
            [{
                'name': 'Test Buyer',
                'country_id': self.env.ref('base.us').id,
                'vat': '12345678992',
                'l10n_tr_edi_edispatch_customs_zip': '34580',
            }],
        )
        self.assertRecordValues(
            picking.l10n_tr_edi_driver_ids,
            [
                {'name': 'Test Driver', 'country_id': self.tr_country_id, 'vat': '11234570890'},
                {'name': 'Test Driver2', 'country_id': self.tr_country_id, 'vat': '22345670891'},
            ],
        )
        self.assertRecordValues(
            picking.l10n_tr_edi_trailer_plate_ids,
            [
                {'name': 'PL01', 'plate_number_type': 'trailer'},
                {'name': 'PL02', 'plate_number_type': 'trailer'},
            ],
        )
