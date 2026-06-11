from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.exceptions import UserError


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestMyDATAPicking(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('gr')
    def setUpClass(cls):
        super().setUpClass()

        cls.env.company.write({
            'name': 'My Greece Company',
            'vat': '047747270',
            'street': 'Akti Miaouli 10',
            'zip': '18538',
            'city': 'Piraeus',
            'l10n_gr_edi_test_env': True,
            'l10n_gr_edi_aade_id': 'odoo_test_mydata',
            'l10n_gr_edi_aade_key': '******************',
        })
        cls.partner_a.write({
            'country_id': cls.env.ref('base.gr').id,
            'vat': '047747210',
        })
        cls.env['res.company'].create({
            'name': 'Greece Partner A',
            'partner_id': cls.partner_a.id,
            'street': 'Othonos 2',
            'zip': '10557',
            'city': 'Athens',
            'l10n_gr_edi_test_env': True,
        })
        cls.warehouse = cls.env['stock.warehouse'].sudo().create({
            'name': 'Greek Warehouse',
            'code': 'GWH',
            'company_id': cls.company.id,
        })

    def _create_mydata_delivery_note(cls, done=True):
        picking = cls.env['stock.picking'].sudo().create({
            'partner_id': cls.partner_a.id,
            'l10n_gr_edi_move_purpose': '1',
            'move_type': 'direct',
            'location_id': cls.warehouse.lot_stock_id.id,
            'location_dest_id': cls.env.ref('stock.stock_location_customers').sudo().id,
            'picking_type_id': cls.warehouse.out_type_id.id,
            'move_ids': [Command.create({
                'product_id': cls.product_a.id,
                'product_uom_qty': 1.0,
            })],
        })
        if done:
            picking.action_confirm()
            picking.action_assign()
            picking.move_ids.quantity = 1.0
            picking.button_validate()
        return picking

    def test_l10n_gr_edi_matching_uom(self):
        picking = self._create_mydata_delivery_note(done=False)
        move = picking.move_ids[0]

        move.uom_id = self.env.ref('uom.product_uom_unit')
        self.assertEqual(move.l10n_gr_edi_measurement_unit, '1')

        move.uom_id = self.env.ref('uom.product_uom_kgm')
        self.assertEqual(move.l10n_gr_edi_measurement_unit, '2')

        move.uom_id = self.env.ref('uom.product_uom_litre')
        self.assertEqual(move.l10n_gr_edi_measurement_unit, '3')

        move.uom_id = self.env.ref('uom.product_uom_meter')
        self.assertEqual(move.l10n_gr_edi_measurement_unit, '4')

        move.uom_id = self.env.ref('uom.product_uom_square_meter')
        self.assertEqual(move.l10n_gr_edi_measurement_unit, '5')

        move.uom_id = self.env.ref('uom.product_uom_cubic_meter')
        self.assertEqual(move.l10n_gr_edi_measurement_unit, '6')

        # uom ton is not valid for myDATA => should be False
        move.uom_id = self.env.ref('uom.product_uom_ton')
        self.assertFalse(move.l10n_gr_edi_measurement_unit)

        picking.button_validate()
        errors = picking._l10n_gr_edi_get_pre_error_dict()
        self.assertIn('l10n_gr_edi_1_missing_uom', errors)

    def test_l10n_gr_edi_picking_pre_errors(self):
        picking = self._create_mydata_delivery_note(done=False)

        self.env.company.l10n_gr_edi_aade_id = False
        self.env.company.street = 'Akti Miaouli'
        self.env.company.zip = False
        self.env.company.vat = False
        picking.partner_id.street = 'Akti Miaouli'
        picking.partner_id.zip = False
        picking.partner_id.vat = False

        picking.button_validate()
        errors = picking._l10n_gr_edi_get_pre_error_dict()
        self.assertIn('l10n_gr_edi_company_no_cred', errors)
        self.assertIn('l10n_gr_edi_company_no_street', errors)
        self.assertIn('l10n_gr_edi_company_no_zip_city', errors)
        self.assertIn('l10n_gr_edi_company_no_vat', errors)
        self.assertIn('l10n_gr_edi_partner_no_street', errors)
        self.assertIn('l10n_gr_edi_partner_no_zip_city', errors)
        self.assertIn('l10n_gr_edi_partner_no_vat', errors)

    def test_l10n_gr_edi_picking_send_success(self):
        picking = self._create_mydata_delivery_note()

        mock_result = {
            0: {
                'mydata_mark': '400001924190891',
                'mydata_url': 'https://mydataapidev.aade.gr/404',
            }
        }
        xml_vals = picking._l10n_gr_edi_get_pickings_xml_vals()
        self.env['l10n_gr_edi.document']._l10n_gr_edi_handle_send_result(picking, mock_result, xml_vals)
        self.assertEqual(picking.l10n_gr_edi_state, 'delivery_note_sent')
        self.assertEqual(picking.l10n_gr_edi_mark, '400001924190891')

    def test_l10n_gr_edi_picking_send_error(self):
        picking = self._create_mydata_delivery_note()

        mock_result = {
            0: {
                'error': '[223] Unsupported invoice type',
            }
        }
        xml_vals = picking._l10n_gr_edi_get_pickings_xml_vals()

        with self.assertRaises(UserError):
            self.env['l10n_gr_edi.document']._l10n_gr_edi_handle_send_result(picking, mock_result, xml_vals)
            picking._l10n_gr_edi_send_delivery_note()
