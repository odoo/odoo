from datetime import datetime

from lxml import etree

from odoo import Command
from odoo.tests import tagged
from odoo.addons.l10n_gr_edi_delivery_note.tests.common import TestMyDATADeliveryNoteCommon

NS = {'inv': 'http://www.aade.gr/myDATA/invoice/v1.0'}


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestMyDATADeliveryNote(TestMyDATADeliveryNoteCommon):

    def test_measurement_unit_mapping(self):
        for xmlid, expected_code in (
            ('uom.product_uom_unit', '1'),
            ('uom.product_uom_kgm', '2'),
            ('uom.product_uom_litre', '3'),
            ('uom.product_uom_meter', '4'),
            ('uom.uom_square_meter', '5'),
            ('uom.product_uom_cubic_meter', '6'),
            ('uom.product_uom_ton', False),  # not supported by myDATA
        ):
            picking = self._create_picking(validate=False, uom=self.env.ref(xmlid))
            self.assertEqual(picking.move_ids.l10n_gr_edi_measurement_unit, expected_code, xmlid)

    def test_default_mydata_values(self):
        self.warehouse.partner_id = self.env['res.partner'].create({
            'name': 'Greek Warehouse Address',
            'street': 'Lefkosias 5',
            'zip': '57009',
            'city': 'Kalochori',
        })
        expected_loading_address = {
            'l10n_gr_edi_loading_address_street': 'Lefkosias',
            'l10n_gr_edi_loading_address_number': '5',
            'l10n_gr_edi_loading_address_zip': '57009',
            'l10n_gr_edi_loading_address_city': 'Kalochori',
        }
        # Picking created by hand
        picking = self._create_picking(validate=False)
        self.assertRecordValues(picking, [{
            **expected_loading_address,
            'l10n_gr_edi_move_purpose': '1',
            'l10n_gr_edi_delivery_address_street': 'Othonos',
            'l10n_gr_edi_delivery_address_number': '2',
            'l10n_gr_edi_delivery_address_zip': '10557',
            'l10n_gr_edi_delivery_address_city': 'Athens',
        }])
        # Picking created by stock, e.g. when a sale order is confirmed
        new_picking_values = picking.move_ids._get_new_picking_values()
        self.assertDictEqual(
            {field: new_picking_values[field] for field in expected_loading_address},
            expected_loading_address,
        )

    def test_pre_errors(self):
        picking = self._create_picking()
        self.assertFalse(
            set(picking._l10n_gr_edi_get_pre_error_dict()) - {'l10n_gr_edi_missing_methodoos_token'},
            "A complete delivery note should have no error besides the provider token.",
        )

        picking = self._create_picking(uom=self.env.ref('uom.product_uom_ton'))
        self.env.company.write({'l10n_gr_edi_aade_id': False, 'street': 'Akti Miaouli', 'zip': False, 'vat': False})
        self.partner_a.write({'street': 'Othonos', 'zip': False, 'vat': False})
        picking.write({
            'name': 'WH/OUT/ABC',
            'l10n_gr_edi_move_purpose': '19',
            'l10n_gr_edi_delivery_address_city': False,
        })

        errors = picking._l10n_gr_edi_get_pre_error_dict()
        for expected_error in (
            'l10n_gr_edi_company_no_cred',
            'l10n_gr_edi_company_no_street',
            'l10n_gr_edi_company_no_zip_city',
            'l10n_gr_edi_company_no_vat',
            'l10n_gr_edi_partner_no_street',
            'l10n_gr_edi_partner_no_zip_city',
            'l10n_gr_edi_partner_no_vat',
            'l10n_gr_edi_invalid_aa',
            'l10n_gr_edi_no_other_move_purpose',
            'l10n_gr_edi_no_delivery_address',
            'l10n_gr_edi_1_missing_uom',
        ):
            self.assertIn(expected_error, errors)

    def test_delivery_note_xml(self):
        picking = self._create_picking(l10n_gr_edi_vehicle_number='ABC1234')
        # 22:30 UTC in winter is already the next day in Greece (UTC+2)
        picking.date_done = datetime(2024, 1, 1, 22, 30, 0)

        xml_content = picking._l10n_gr_edi_generate_delivery_note_xml(issue_datetime=datetime(2024, 1, 1, 22, 45, 0))
        self.assertTrue(xml_content.startswith(b"<?xml version='1.0' encoding='UTF-8' standalone='yes'?>"))

        root = etree.fromstring(xml_content)
        series, aa = picking.name.rsplit('/', 1)

        def value(xpath):
            return root.findtext(xpath, namespaces=NS)

        self.assertEqual(value('.//inv:issuer/inv:vatNumber'), '047747270')
        self.assertEqual(value('.//inv:issuer/inv:name'), 'Ελληνική Εταιρεία')
        self.assertEqual(value('.//inv:issuer/inv:address/inv:city'), 'Πειραιάς')
        self.assertEqual(value('.//inv:counterpart/inv:name'), 'Πελάτης Α.Ε.')
        self.assertEqual(value('.//inv:invoiceHeader/inv:series'), series.replace('/', '_'))
        self.assertEqual(value('.//inv:invoiceHeader/inv:aa'), aa)
        self.assertEqual(value('.//inv:invoiceHeader/inv:invoiceType'), '9.3')
        self.assertEqual(value('.//inv:invoiceHeader/inv:issueDate'), '2024-01-02')
        self.assertEqual(value('.//inv:invoiceHeader/inv:dispatchDate'), '2024-01-02')
        self.assertEqual(value('.//inv:invoiceHeader/inv:dispatchTime'), '00:30:00')
        self.assertEqual(value('.//inv:invoiceHeader/inv:vehicleNumber'), 'ABC1234')
        self.assertEqual(value('.//inv:invoiceHeader/inv:movePurpose'), '1')
        self.assertIsNone(root.find('.//inv:invoiceHeader/inv:otherMovePurposeTitle', NS))
        self.assertIsNone(root.find('.//inv:invoiceHeader/inv:currency', NS))
        self.assertIsNone(root.find('.//inv:paymentMethods', NS))
        self.assertEqual(value('.//inv:otherDeliveryNoteHeader/inv:deliveryAddress/inv:street'), 'Othonos')
        self.assertEqual(value('.//inv:invoiceDetails/inv:quantity'), '2.0')
        self.assertEqual(value('.//inv:invoiceDetails/inv:measurementUnit'), '1')
        self.assertEqual(value('.//inv:invoiceDetails/inv:vatCategory'), '8')
        self.assertEqual(value('.//inv:invoiceSummary/inv:totalGrossValue'), '0')

    def test_return_move_purpose(self):
        picking = self._create_picking()
        return_wizard = self.env['stock.return.picking'].with_context(
            active_id=picking.id,
            active_model='stock.picking',
        ).create({})
        return_wizard.product_return_moves.quantity = 1.0
        return_picking = self.env['stock.picking'].browse(return_wizard.action_create_returns()['res_id'])
        self.assertEqual(return_picking.l10n_gr_edi_move_purpose, '5')

    def test_invoice_connected_marks(self):
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({'product_id': self.product_a.id, 'product_uom_qty': 2.0})],
        })
        sale_order.action_confirm()
        picking = sale_order.picking_ids
        picking.move_ids.quantity = 2.0
        picking.move_ids.picked = True
        picking.button_validate()
        self.env['l10n_gr_edi.document'].create({
            'picking_id': picking.id,
            'state': 'delivery_note_sent',
            'mydata_mark': '400001976153455',
        })

        invoice = sale_order._create_invoices()
        invoice.invoice_line_ids.write({'l10n_gr_edi_cls_category': 'category1_1', 'l10n_gr_edi_cls_type': 'E3_561_001'})
        invoice.action_post()
        credit_note = invoice._reverse_moves()
        credit_note.action_post()

        def connected_marks(move):
            xml_content = move._l10n_gr_edi_generate_xml_content(
                'l10n_gr_edi.mydata_invoice',
                move._l10n_gr_edi_get_invoices_xml_vals(),
            )
            return [mark.text for mark in etree.fromstring(xml_content).iterfind('.//inv:invoiceHeader/inv:multipleConnectedMarks', NS)]

        # The invoice references the MARK of the delivery note it bills
        self.assertEqual(connected_marks(invoice), ['400001976153455'])
        # Credit notes only reference the invoice they correct
        self.assertEqual(connected_marks(credit_note), [])
