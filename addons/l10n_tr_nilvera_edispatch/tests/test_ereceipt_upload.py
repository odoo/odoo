import base64
from unittest.mock import patch

from odoo import fields, Command
from odoo.tests import tagged
from odoo.tools import file_open

from odoo.addons.stock.tests.common import TestStockCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestTRNilveraEreceiptUpload(TestStockCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tr_country_id = cls.env.ref('base.tr').id
        cls.receipt_partner = cls.PartnerObj.with_context(no_vat_validation=True).create({
            'name': 'Test Kurum İki',
            'country_id': cls.tr_country_id,
            'vat': '1234567802',
        })
        cls.driver_partner = cls.PartnerObj.with_context(no_vat_validation=True).create({
            'name': 'Test Driver',
            'country_id': cls.tr_country_id,
            'vat': '11234570890',
        })
        cls.uom_grm = cls.env.ref('uom.product_uom_gram').id
        cls.move_product = cls.ProductObj.create({
            'name': 'Product in GRM',
            'uom_id': cls.uom_grm,
        })
        cls.uom_unit = cls.env.ref('uom.product_uom_unit').id
        cls.uom_kgm = cls.env.ref('uom.product_uom_kgm').id

    def test_ereceipt_xml_with_timezone_offset_upload(self):
        """Nilvera sends the time with fractional seconds and an offset, e.g. `11:30:00.0000000+03:00`."""
        with file_open('l10n_tr_nilvera_edispatch/tests/test_files/test_ereceipt_timezone_offset.xml', 'rb') as f:
            ereceipt_xml = self.env['ir.attachment'].create({
                'name': 'test_ereceipt_timezone_offset_upload.xml',
                'type': 'binary',
                'raw': f.read(),
            })

        picking, files_with_errors = self.env['stock.picking']._l10n_tr_create_receipts_from_attachment(ereceipt_xml)
        self.assertEqual(files_with_errors, [])
        self.assertRecordValues(
            picking,
            [{
                'scheduled_date': fields.Datetime.from_string('2025-07-29 11:30:00'),
                'origin': 'EIT2025000000101',
            }],
        )

    def test_ereceipt_xml_without_errors_upload(self):
        with file_open('l10n_tr_nilvera_edispatch/tests/test_files/test_ereceipt.xml', 'rb') as f:
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
            picking.l10n_tr_nilvera_seller_supplier_id,
            [{
                'name': 'Test Seller',
                'country_id': self.tr_country_id,
                'vat': '1234567800',
                'zip': '62800',
            }],
        )
        self.assertRecordValues(
            picking.l10n_tr_nilvera_buyer_id,
            [{
                'name': 'Test Buyer',
                'country_id': self.env.ref('base.us').id,
                'vat': '12345678992',
                'l10n_tr_nilvera_edispatch_customs_zip': '34580',
            }],
        )
        self.assertRecordValues(
            picking.l10n_tr_nilvera_driver_ids,
            [
                {'name': 'Test Driver', 'country_id': self.tr_country_id, 'vat': '11234570890'},
                {'name': 'Test Driver2', 'country_id': self.tr_country_id, 'vat': '22345670891'},
            ],
        )
        self.assertRecordValues(
            picking.l10n_tr_nilvera_trailer_plate_ids,
            [
                {'name': 'PL01', 'plate_number_type': 'trailer'},
                {'name': 'PL02', 'plate_number_type': 'trailer'},
            ],
        )

    def test_cron_nilvera_get_edispatch_purchase_pdf(self):
        """Test that the cron fetches the e-Dispatch PDF and stores it on the picking."""
        self.receipt_partner.write({
            'state_id': self.env.ref('base.state_tr_01').id,
            'city': 'Adana',
            'zip': '321123',
            'street': '12th dec. street',
        })
        self.env.company.write({
            'vat': '1234567890',
            'country_id': self.tr_country_id,
        })
        warehouse = self.env.user._get_default_warehouse_id()
        picking = self.env['stock.picking'].create({
            'picking_type_id': warehouse.out_type_id.id,
            'location_id': self.env.ref('stock.stock_location_customers').id,
            'location_dest_id': warehouse.lot_stock_id.id,
            'partner_id': self.receipt_partner.id,
            'move_ids': [Command.create({
                'product_id': self.move_product.id,
                'product_uom_qty': 1,
            })],
            'l10n_tr_nilvera_carrier_id': self.driver_partner.id,
        })
        picking.action_confirm()
        picking.button_validate()
        picking.action_generate_l10n_tr_edispatch_xml()
        picking.l10n_tr_nilvera_send_status = 'pdf_not_fetched'

        self.assertTrue(picking.l10n_tr_nilvera_edispatch_xml_file)
        self.assertFalse(picking.l10n_tr_nilvera_edispatch_pdf_file)

        # Mock the Nilvera response to avoid making a real HTTP request.
        with patch(
            'odoo.addons.l10n_tr_nilvera_edispatch.models.stock_picking._get_nilvera_client'
        ) as mock_client:
            mock_response = b'%PDF-1.4\n% Sample PDF'
            client = mock_client.return_value.__enter__.return_value
            client.request.return_value = base64.b64encode(mock_response)
            picking._cron_nilvera_get_edispatch_purchase_pdf()

        self.assertTrue(picking.l10n_tr_nilvera_edispatch_pdf_file)
        self.assertEqual(picking.l10n_tr_nilvera_send_status, 'succeed')
