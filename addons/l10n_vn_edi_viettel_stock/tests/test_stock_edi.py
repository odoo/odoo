# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
from unittest.mock import patch

from freezegun import freeze_time

from odoo.exceptions import UserError
from odoo import Command
from odoo.tests import TransactionCase, tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestVNEDIStock(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company_vn = cls.env['res.company'].create({
            'name': 'VN Test Company',
            'country_id': cls.env.ref('base.vn').id,
            'street': '3 Alley 45 Phan Dinh Phung',
            'vat': '0100109106-506',
            'phone': '6266 1275',
            'email': 'test@test.vn',
            'l10n_vn_edi_username': 'test_user',
            'l10n_vn_edi_password': 'test_pass',
            'l10n_vn_edi_send_transfer_note': True,
        })

        cls.symbol = cls.env['l10n_vn_edi_viettel.sinvoice.symbol'].create({
            'name': 'K24NTU',
            'invoice_template_code': '1/001',
            'company_id': cls.company_vn.id,
        })
        cls.company_vn.l10n_vn_edi_stock_default_sinvoice_symbol_id = cls.symbol

        cls.wh1 = cls.env['stock.warehouse'].search(
            [('company_id', '=', cls.company_vn.id)], limit=1,
        )
        cls.wh2 = cls.env['stock.warehouse'].create({
            'name': 'Warehouse Two',
            'code': 'WH2',
            'company_id': cls.company_vn.id,
        })

        cls.product_a = cls.env['product.product'].create({
            'name': 'Product A',
            'default_code': 'PROD-A',
            'lst_price': 500_000.0,
        })

        cls.partner_vn = cls.env['res.partner'].create({
            'name': 'Test Buyer',
            'street': '10 Pho Hue',
            'country_id': cls.env.ref('base.vn').id,
            'phone': '0912345678',
            'email': 'buyer@example.vn',
        })

    # =========================================================================
    # Helpers
    # =========================================================================

    def _make_inter_warehouse_picking(self, state='done', partner=None, qty=3.0):
        """Create a stock picking from wh1 to wh2."""
        picking = self.env['stock.picking'].with_company(self.company_vn).create({
            'picking_type_id': self.wh1.int_type_id.id,
            'location_id': self.wh1.lot_stock_id.id,
            'location_dest_id': self.wh2.lot_stock_id.id,
            'company_id': self.company_vn.id,
            'partner_id': partner.id if partner else False,
            'move_ids': [Command.create({
                'product_id': self.product_a.id,
                'product_uom_qty': qty,
                'uom_id': self.product_a.uom_id.id,
                'location_id': self.wh1.lot_stock_id.id,
                'location_dest_id': self.wh2.lot_stock_id.id,
            })],
        })
        picking.action_confirm()
        picking.action_assign()
        if state == 'done':
            picking.move_line_ids.write({'quantity': qty})
            picking._action_done()
        return picking

    def _send_picking(self, picking):
        """Run the send wizard with mocked API calls."""
        token_resp = {'access_token': 'tok123', 'expires_in': '600'}
        create_resp = {'invoiceNo': 'K24NTU01', 'reservationCode': 'SEC456'}
        zip_resp = {'fileToBytes': base64.b64encode(b'PK\x03\x04fake_zip').decode(), 'fileName': 'inv.zip'}
        pdf_resp = {'fileToBytes': base64.b64encode(b'%PDF-fake').decode(), 'fileName': 'inv.pdf'}
        xml_data = {'name': 'inv.xml', 'raw': b'<xml/>', 'mimetype': 'text/xml'}

        with patch('odoo.addons.l10n_vn_edi_viettel.models.res_company.ResCompany._l10n_vn_edi_get_access_token', return_value=(token_resp, None)), \
             patch('odoo.addons.l10n_vn_edi_viettel.models.sinvoice_service.SInvoiceService.create_invoice', return_value=(create_resp, None)), \
             patch('odoo.addons.l10n_vn_edi_viettel.models.sinvoice_service.SInvoiceService.get_invoice_file', side_effect=[(zip_resp, None), (pdf_resp, None)]), \
             patch('odoo.addons.l10n_vn_edi_viettel.models.sinvoice_service.SInvoiceService.extract_xml_from_zip', return_value=(xml_data, None)):
            wizard = self.env['l10n_vn_edi_viettel_stock.send_wizard'].create({
                'picking_id': picking.id,
            })
            wizard.action_send()

    # =========================================================================
    # Computed Fields
    # =========================================================================

    def test_show_send_button_inter_warehouse(self):
        """Send button shows for inter-warehouse pickings but not for incoming receipts."""
        inter_wh_picking = self._make_inter_warehouse_picking(state='done')
        self.assertTrue(inter_wh_picking.l10n_vn_edi_show_send_button)

        # Incoming receipt: supplier -> wh1 stock should not show the button
        supplier_loc = self.env.ref('stock.stock_location_suppliers')
        incoming_picking = self.env['stock.picking'].with_company(self.company_vn).create({
            'picking_type_id': self.wh1.in_type_id.id,
            'location_id': supplier_loc.id,
            'location_dest_id': self.wh1.lot_stock_id.id,
            'company_id': self.company_vn.id,
            'move_ids': [Command.create({
                'product_id': self.product_a.id,
                'product_uom_qty': 1.0,
                'uom_id': self.product_a.uom_id.id,
                'location_id': supplier_loc.id,
                'location_dest_id': self.wh1.lot_stock_id.id,
            })],
        })
        incoming_picking.action_confirm()
        self.assertFalse(incoming_picking.l10n_vn_edi_show_send_button)

    def test_show_send_button_transit(self):
        """Send button shows for transit-destination pickings and hides after sending."""
        transit_loc = self.company_vn.internal_transit_location_id
        picking = self.env['stock.picking'].with_company(self.company_vn).create({
            'picking_type_id': self.wh1.int_type_id.id,
            'location_id': self.wh1.lot_stock_id.id,
            'location_dest_id': transit_loc.id,
            'company_id': self.company_vn.id,
            'move_ids': [Command.create({
                'product_id': self.product_a.id,
                'product_uom_qty': 1.0,
                'uom_id': self.product_a.uom_id.id,
                'location_id': self.wh1.lot_stock_id.id,
                'location_dest_id': transit_loc.id,
            })],
        })
        picking.action_confirm()
        picking.action_assign()
        self.assertTrue(picking.l10n_vn_edi_show_send_button)

        # After sending, button should be hidden
        picking.l10n_vn_edi_is_sent = True
        picking.invalidate_recordset(['l10n_vn_edi_show_send_button'])
        self.assertFalse(picking.l10n_vn_edi_show_send_button)

    def test_symbol_resolution_warehouse_then_company(self):
        """Warehouse symbol takes priority over company default; non-VN company gives False."""
        # Create a second symbol and assign it to wh1
        wh1_symbol = self.env['l10n_vn_edi_viettel.sinvoice.symbol'].create({
            'name': 'K24WH1',
            'invoice_template_code': '2/001',
            'company_id': self.company_vn.id,
        })
        self.wh1.l10n_vn_edi_sinvoice_symbol_id = wh1_symbol

        picking = self._make_inter_warehouse_picking(state='assigned')
        self.assertEqual(picking.l10n_vn_edi_symbol_id, wh1_symbol)

        # Switching to a warehouse with no symbol falls back to company default
        picking.picking_type_id = self.wh2.int_type_id
        self.assertEqual(picking.l10n_vn_edi_symbol_id, self.symbol)

        # Non-VN company: symbol must be False
        us_company = self.env['res.company'].create({
            'name': 'US Company',
            'country_id': self.env.ref('base.us').id,
        })
        us_wh = self.env['stock.warehouse'].search(
            [('company_id', '=', us_company.id)], limit=1,
        )
        us_picking = self.env['stock.picking'].with_company(us_company).create({
            'picking_type_id': us_wh.int_type_id.id,
            'location_id': us_wh.lot_stock_id.id,
            'location_dest_id': us_wh.lot_stock_id.id,
            'company_id': us_company.id,
        })
        self.assertFalse(us_picking.l10n_vn_edi_symbol_id)

    def test_auto_population_of_fields(self):
        """Well-known custom field tags are pre-populated in the wizard from picking data."""
        picking = self._make_inter_warehouse_picking(state='assigned')
        custom_fields_from_api = [
            {'keyTag': 'economicContractNo', 'keyLabel': 'Economic Contract No.', 'isRequired': False, 'isSeller': True},
            {'keyTag': 'exportAt', 'keyLabel': 'Export Warehouse', 'isRequired': False, 'isSeller': True},
            {'keyTag': 'importAt', 'keyLabel': 'Import Warehouse', 'isRequired': False, 'isSeller': True},
        ]
        token_resp = {'access_token': 'tok', 'expires_in': '600'}
        with patch('odoo.addons.l10n_vn_edi_viettel.models.res_company.ResCompany._l10n_vn_edi_get_access_token', return_value=(token_resp, None)), \
             patch('odoo.addons.l10n_vn_edi_viettel.models.sinvoice_service.SInvoiceService.get_custom_fields', return_value=(custom_fields_from_api, None)):
            action = picking.action_l10n_vn_send_to_sinvoice()

        wizard = self.env['l10n_vn_edi_viettel_stock.send_wizard'].browse(action['res_id'])
        values_by_tag = {line.key_tag: line.value for line in wizard.template_field_ids}
        self.assertEqual(values_by_tag.get('economicContractNo'), picking.name)
        self.assertEqual(values_by_tag.get('exportAt'), self.wh1.name)
        self.assertEqual(values_by_tag.get('importAt'), self.wh2.name)

    # =========================================================================
    # Configuration Validation
    # =========================================================================

    def test_check_configuration_errors(self):
        """Each missing/invalid field produces the correct error."""
        picking = self._make_inter_warehouse_picking()

        # 1. Missing credentials
        self.company_vn.l10n_vn_edi_username = False
        self.assertTrue(picking._l10n_vn_edi_check_configuration())
        self.company_vn.l10n_vn_edi_username = 'test_user'

        # 2. Missing VAT
        self.company_vn.vat = False
        errors = picking._l10n_vn_edi_check_configuration()
        self.assertTrue(any('VAT' in e for e in errors))
        self.company_vn.vat = '0100109106-506'

        # 3. No symbol
        picking.l10n_vn_edi_symbol_id = False
        errors = picking._l10n_vn_edi_check_configuration()
        self.assertTrue(any('symbol' in e.lower() for e in errors))
        picking.l10n_vn_edi_symbol_id = self.symbol

        # 4. Symbol missing template code
        self.symbol.invoice_template_code = False
        errors = picking._l10n_vn_edi_check_configuration()
        self.assertTrue(any('template' in e.lower() for e in errors))
        self.symbol.invoice_template_code = '1/001'

        # 5. Missing company address
        self.company_vn.street = False
        errors = picking._l10n_vn_edi_check_configuration()
        self.assertTrue(any('street' in e.lower() or 'country' in e.lower() for e in errors))
        self.company_vn.street = '3 Alley 45 Phan Dinh Phung'

    def test_check_configuration_valid(self):
        """A fully valid picking returns no configuration errors."""
        picking = self._make_inter_warehouse_picking()
        errors = picking._l10n_vn_edi_check_configuration()
        self.assertEqual(errors, [])

    # =========================================================================
    # JSON Generation
    # =========================================================================

    @freeze_time('2026-01-01')
    def test_json_general_seller_buyer_info(self):
        """JSON payload has correct general info, seller info, buyer info, and payments."""
        picking = self._make_inter_warehouse_picking(partner=self.partner_vn)
        data = picking._l10n_vn_edi_generate_transfer_note_json()

        general = data['generalInvoiceInfo']
        self.assertEqual(general['templateCode'], '1/001')
        self.assertEqual(general['invoiceSeries'], 'K24NTU')
        self.assertEqual(general['adjustmentType'], '1')
        self.assertTrue(general['paymentStatus'])
        self.assertTrue(general['cusGetInvoiceRight'])
        self.assertIn('transactionUuid', general)

        self.assertEqual(data['buyerInfo']['buyerName'], 'Test Buyer')
        self.assertEqual(data['sellerInfo']['sellerTaxCode'], self.company_vn.vat)
        self.assertEqual(data['payments'], [{'paymentMethodName': 'TM/CK'}])

    @freeze_time('2026-01-01')
    def test_json_buyer_not_get_invoice_flag(self):
        """Picking without partner results in buyerNotGetInvoice flag."""
        picking = self._make_inter_warehouse_picking(partner=None)
        data = picking._l10n_vn_edi_generate_transfer_note_json()
        self.assertEqual(data['buyerInfo'], {'buyerNotGetInvoice': 1})

    @freeze_time('2026-01-01')
    def test_json_item_info_and_tax_breakdowns(self):
        """Items are correctly built; zero-qty moves are skipped; tax is always -2."""
        picking = self._make_inter_warehouse_picking(qty=3.0)

        # Add a zero-quantity move; it must be excluded from itemInfo
        self.env['stock.move'].with_company(self.company_vn).create({
            'product_id': self.product_a.id,
            'product_uom_qty': 0.0,
            'uom_id': self.product_a.uom_id.id,
            'picking_id': picking.id,
            'location_id': picking.location_id.id,
            'location_dest_id': picking.location_dest_id.id,
        })

        data = picking._l10n_vn_edi_generate_transfer_note_json()

        self.assertEqual(len(data['itemInfo']), 1)
        item = data['itemInfo'][0]
        self.assertEqual(item['itemCode'], 'PROD-A')
        self.assertEqual(item['quantity'], 3.0)
        self.assertEqual(item['unitPrice'], 500_000.0)
        self.assertEqual(item['itemTotalAmountWithoutTax'], 1_500_000.0)
        self.assertEqual(item['taxPercentage'], -2)
        self.assertEqual(item['taxAmount'], 0)

        self.assertEqual(data['taxBreakdowns'], [{
            'taxPercentage': -2,
            'taxableAmount': 1_500_000.0,
            'taxAmount': 0,
            'taxableAmountPos': True,
            'taxAmountPos': True,
        }])

    # =========================================================================
    # Send & File Fetch
    # =========================================================================

    def test_send_transfer_note_success(self):
        """Successful send updates state, invoice number, and creates all attachments."""
        picking = self._make_inter_warehouse_picking()
        self._send_picking(picking)

        self.assertTrue(picking.l10n_vn_edi_is_sent)
        self.assertEqual(picking.l10n_vn_edi_invoice_number, 'K24NTU01')
        self.assertEqual(picking.l10n_vn_edi_reservation_code, 'SEC456')
        self.assertTrue(picking.l10n_vn_edi_sinvoice_file_id)
        self.assertTrue(picking.l10n_vn_edi_sinvoice_xml_file_id)
        self.assertTrue(picking.l10n_vn_edi_sinvoice_pdf_file_id)

    def test_send_transfer_note_api_error(self):
        """API errors raise UserError and do not mutate picking state."""
        picking = self._make_inter_warehouse_picking()

        # Token fetch failure
        with patch('odoo.addons.l10n_vn_edi_viettel.models.res_company.ResCompany._l10n_vn_edi_get_access_token', return_value=(None, 'Auth failed')):
            wizard = self.env['l10n_vn_edi_viettel_stock.send_wizard'].create({
                'picking_id': picking.id,
            })
            with self.assertRaisesRegex(UserError, 'Auth failed'):
                wizard.action_send()
        self.assertFalse(picking.l10n_vn_edi_is_sent)

        # BAD_REQUEST error from create_invoice
        with patch('odoo.addons.l10n_vn_edi_viettel.models.res_company.ResCompany._l10n_vn_edi_get_access_token', return_value=({'access_token': 'tok', 'expires_in': '600'}, None)), \
             patch('odoo.addons.l10n_vn_edi_viettel.models.sinvoice_service.SInvoiceService.create_invoice', return_value=({}, 'Error: BAD_REQUEST_STRING_VALUE_INFO_UPDATE_REQUIRED details')):
            wizard = self.env['l10n_vn_edi_viettel_stock.send_wizard'].create({
                'picking_id': picking.id,
            })
            with self.assertRaisesRegex(UserError, 'required template fields'):
                wizard.action_send()
        self.assertFalse(picking.l10n_vn_edi_is_sent)
