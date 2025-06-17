import datetime

from freezegun import freeze_time

from odoo import Command
from odoo.tests import tagged
from .common import TestL10nEsEdiVerifactuCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nEsEdiVerifactuJson(TestL10nEsEdiVerifactuCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.fakenow = datetime.datetime(2024, 12, 5)
        cls.startClassPatcher(freeze_time(cls.fakenow))

    def test_huella_generation(self):
        """
        Test cases taken from the examples in the AEAT documentation about fingerprint ("huella") generation:
        'Detalle de las especificaciones técnicas para generación de la huella o hash de los registros de facturación'
        """
        render_values = {
            'cancellation': False,
            'record_type': 'RegistroAlta',

            'RegistroAlta': {
                'IDFactura': {
                    'IDEmisorFactura': "  89890001K  ",
                    'NumSerieFactura': "  12345678/G33  ",
                    'FechaExpedicionFactura': "  01-01-2024  ",
                },
                'TipoFactura': "  F1  ",
                'CuotaTotal': "  12.35  ",
                'ImporteTotal': "  123.45  ",
                'Encadenamiento': {
                    'PrimerRegistro': 'S',
                },
                'FechaHoraHusoGenRegistro': "  2024-01-01T19:20:30+01:00  ",
            },
        }
        fingerprint = self.env['l10n_es_edi_verifactu.document']._fingerprint(render_values)
        self.assertEqual(fingerprint, "3C464DAF61ACB827C65FDA19F352A4E3BDC2C640E9E9FC4CC058073F38F12F60")

        render_values = {
            'cancellation': False,
            'record_type': 'RegistroAlta',

            'RegistroAlta': {
                'IDFactura': {
                    'IDEmisorFactura': "  89890001K  ",
                    'NumSerieFactura': "  12345679/G34  ",
                    'FechaExpedicionFactura': "  01-01-2024  ",
                },
                'TipoFactura': "  F1  ",
                'CuotaTotal': "  12.35  ",
                'ImporteTotal': "  123.45  ",
                'Encadenamiento': {
                    'RegistroAnterior': {
                        'Huella': "3C464DAF61ACB827C65FDA19F352A4E3BDC2C640E9E9FC4CC058073F38F12F60",
                    },
                },
                'FechaHoraHusoGenRegistro': "  2024-01-01T19:20:35+01:00  ",
            },
        }
        fingerprint = self.env['l10n_es_edi_verifactu.document']._fingerprint(render_values)
        self.assertEqual(fingerprint, "F7B94CFD8924EDFF273501B01EE5153E4CE8F259766F88CF6ACB8935802A2B97")

        render_values = {
            'cancellation': True,
            'record_type': 'RegistroAnulacion',

            'RegistroAnulacion': {
                'IDFactura': {
                    'IDEmisorFacturaAnulada': "  89890001K  ",
                    'NumSerieFacturaAnulada': "  12345679/G34  ",
                    'FechaExpedicionFacturaAnulada': "  01-01-2024  ",
                },
                'Encadenamiento': {
                    'RegistroAnterior': {
                        'Huella': "F7B94CFD8924EDFF273501B01EE5153E4CE8F259766F88CF6ACB8935802A2B97",
                    },
                },
                'FechaHoraHusoGenRegistro': "  2024-01-01T19:20:40+01:00  ",
            },
        }
        fingerprint = self.env['l10n_es_edi_verifactu.document']._fingerprint(render_values)
        self.assertEqual(fingerprint, "177547C0D57AC74748561D054A9CEC14B4C4EA23D1BEFD6F2E69E3A388F90C68")

    def test_invoice_1_and_credit_note(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2019-01-30',
            'date': '2019-01-30',
            'partner_id': self.partner_b.id,  # Spanish customer
            'invoice_line_ids': [
                Command.create({'product_id': self.product_1.id, 'price_unit': 100.0, 'tax_ids': [Command.set(self.tax21_goods.ids)]}),
                Command.create({'product_id': self.product_1.id, 'price_unit': 200.0, 'tax_ids': [Command.set(self.tax21_services.ids)]}),
                Command.create({'product_id': self.product_1.id, 'price_unit': 1000.0, 'tax_ids': [Command.set(self.tax10_goods.ids)]}),
            ],
        })
        invoice.action_post()

        document = invoice._l10n_es_edi_verifactu_create_document()
        self.assertFalse(document.errors)
        with self._mock_zeep_registration_operation_certificate_issue():
            batch_dict, _info = document._send_as_batch()
        self.assertEqual(batch_dict, self._json_file_to_dict('l10n_es_edi_verifactu/tests/files/test_invoice_1.json'))

        # Test the credit note
        self.env['account.move.reversal'].with_company(self.company).create(
            {
                'move_ids': [Command.set((invoice.id,))],
                'date': '2019-02-10',
                'journal_id': invoice.journal_id.id,
            }
        ).reverse_moves()
        credit_note = invoice.reversal_move_id
        credit_note.write({
            'l10n_es_edi_verifactu_refund_reason': 'R1',
            'invoice_date': '2019-02-11',
        })
        credit_note.action_post()

        document = credit_note._l10n_es_edi_verifactu_create_document()
        self.assertFalse(document.errors)
        with self._mock_zeep_registration_operation_certificate_issue():
            batch_dict, _info = document._send_as_batch()
        self.assertEqual(batch_dict, self._json_file_to_dict('l10n_es_edi_verifactu/tests/files/test_invoice_1_credit_note.json'))

    def test_invoice_1_and_substitution(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2019-01-30',
            'date': '2019-01-30',
            'partner_id': self.partner_b.id,  # Spanish customer
            'invoice_line_ids': [
                Command.create({'product_id': self.product_1.id, 'price_unit': 100.0, 'tax_ids': [Command.set(self.tax21_goods.ids)]}),
                Command.create({'product_id': self.product_1.id, 'price_unit': 200.0, 'tax_ids': [Command.set(self.tax21_services.ids)]}),
                Command.create({'product_id': self.product_1.id, 'price_unit': 1000.0, 'tax_ids': [Command.set(self.tax10_goods.ids)]}),
            ],
        })
        invoice.action_post()

        document = invoice._l10n_es_edi_verifactu_create_document()
        self.assertFalse(document.errors)
        with self._mock_zeep_registration_operation_certificate_issue():
            batch_dict, _info = document._send_as_batch()
        self.assertEqual(batch_dict, self._json_file_to_dict('l10n_es_edi_verifactu/tests/files/test_invoice_1.json'))

        # Create a reversal and a substitution move
        self.env['account.move.reversal'].with_company(self.company).create(
            {
                'move_ids': [Command.set((invoice.id,))],
                'date': '2019-02-10',
                'journal_id': invoice.journal_id.id,
            }
        ).reverse_moves(is_modify=True)

        credit_note = invoice.reversal_move_id
        document = credit_note._l10n_es_edi_verifactu_create_document()
        self.assertFalse(document.errors)
        with self._mock_zeep_registration_operation_certificate_issue():
            batch_dict, _info = document._send_as_batch()
        self.assertEqual(batch_dict, self._json_file_to_dict('l10n_es_edi_verifactu/tests/files/test_invoice_1_reversal_for_substitution.json'))

        substitution_move = invoice.l10n_es_edi_verifactu_substitution_move_id
        substitution_move.invoice_line_ids[0].price_unit = 50
        substitution_move.write({
            'l10n_es_edi_verifactu_refund_reason': 'R1',
            'invoice_date': '2019-02-11',
        })
        substitution_move.action_post()
        document = substitution_move._l10n_es_edi_verifactu_create_document()
        self.assertFalse(document.errors)
        with self._mock_zeep_registration_operation_certificate_issue():
            batch_dict, _info = document._send_as_batch()
        self.assertEqual(batch_dict, self._json_file_to_dict('l10n_es_edi_verifactu/tests/files/test_invoice_1_correction_substitution.json'))

    def test_invoice_2(self):
        """
        I.e. test that the following are handled correctly
          * Recargo de equivalencia taxes
          * 'FechaOperacion' field (set as `delivery_date` in case it is different from the `invoice_date`)
        """
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2019-01-30',
            'delivery_date': '2019-02-01',
            'date': '2019-01-30',
            'partner_id': self.partner_b.id,  # Spanish customer
            'invoice_line_ids': [
                Command.create({'product_id': self.product_1.id, 'price_unit': 100.0, 'tax_ids': [Command.set((self.tax10_goods + self.tax1p4_services_recargo).ids)]}),
                Command.create({'product_id': self.product_1.id, 'price_unit': 200.0, 'tax_ids': [Command.set((self.tax21_services + self.tax5p2_services_recargo).ids)]}),
            ],
        })
        invoice.action_post()

        document = invoice._l10n_es_edi_verifactu_create_document()
        self.assertFalse(document.errors)
        with self._mock_zeep_registration_operation_certificate_issue():
            batch_dict, _info = document._send_as_batch()
        self.assertEqual(batch_dict, self._json_file_to_dict('l10n_es_edi_verifactu/tests/files/test_invoice_2.json'))

    def test_invoice_3(self):
        """
        Test withholding / retention taxes (taxes with `l10n_es_type` 'retencion').
          * We need to ignore them in the generation of the XML
          * We need ignore them for the total in the QR code
        """
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2019-01-30',
            'date': '2019-01-30',
            'partner_id': self.partner_b.id,  # Spanish customer
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_1.id,
                    'price_unit': 1000.0,
                    'tax_ids': [Command.set((self.tax10_goods + self.tax1_withholding).ids)]
                }),
            ],
        })
        invoice.action_post()
        self.assertEqual(invoice.amount_total, 1090.0)

        document = invoice._l10n_es_edi_verifactu_create_document()
        self.assertFalse(document.errors)

        expected_qr_code_url = '/report/barcode/?barcode_type=QR&value=https%3A%2F%2Fprewww2.aeat.es%2Fwlpl%2FTIKE-CONT%2FValidarQR%3Fnif%3D59962470K%26numserie%3DINV%252F2019%252F00001%26fecha%3D30-01-2019%26importe%3D1100.00&barLevel=M&width=180&height=180'
        self.assertEqual(invoice.l10n_es_edi_verifactu_qr_code, expected_qr_code_url)

        with self._mock_zeep_registration_operation_certificate_issue():
            batch_dict, _info = document._send_as_batch()
        self.assertEqual(batch_dict, self._json_file_to_dict('l10n_es_edi_verifactu/tests/files/test_invoice_3.json'))

    def test_invoice_multicurrency_1(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2019-01-30',
            'date': '2019-01-30',
            'currency_id': self.currency_data['currency'].id,
            'partner_id': self.partner_a.id,  # Belgian customer
            'invoice_line_ids': [
                Command.create({'product_id': self.product_1.id, 'price_unit': 100.0, 'tax_ids': [Command.set(self.tax21_goods.ids)]}),
                Command.create({'product_id': self.product_1.id, 'price_unit': 200.0, 'tax_ids': [Command.set(self.tax21_services.ids)]}),
                Command.create({'product_id': self.product_1.id, 'price_unit': 1000.0, 'tax_ids': [Command.set(self.tax10_goods.ids)]}),
            ],
        })
        invoice.action_post()

        document = invoice._l10n_es_edi_verifactu_create_document()
        self.assertFalse(document.errors)
        with self._mock_zeep_registration_operation_certificate_issue():
            batch_dict, _info = document._send_as_batch()
        self.assertEqual(batch_dict, self._json_file_to_dict('l10n_es_edi_verifactu/tests/files/test_invoice_multi_currency_1.json'))

    def test_multiple_invoices_with_predecessor(self):
        invoices = self.env['account.move'].create([
            {
                'move_type': 'out_invoice',
                'invoice_date': '2019-02-01',
                'date': '2019-01-30',
                'partner_id': self.partner_b.id,  # Spanish customer
                'invoice_line_ids': [
                    Command.create({'product_id': self.product_1.id, 'price_unit': 100.0, 'tax_ids': [Command.set(self.tax21_goods.ids)]}),
                    Command.create({'product_id': self.product_1.id, 'price_unit': 200.0, 'tax_ids': [Command.set(self.tax21_services.ids)]}),
                    Command.create({'product_id': self.product_1.id, 'price_unit': 1000.0, 'tax_ids': [Command.set(self.tax10_goods.ids)]}),
                ],
            },
            {
                'move_type': 'out_invoice',
                'invoice_date': '2019-02-02',
                'date': '2019-01-30',
                'partner_id': self.partner_b.id,  # Spanish customer
                'invoice_line_ids': [
                    Command.create({'product_id': self.product_1.id, 'price_unit': 100.0, 'tax_ids': [Command.set(self.tax21_goods.ids)]}),
                    Command.create({'product_id': self.product_1.id, 'price_unit': 200.0, 'tax_ids': [Command.set(self.tax21_services.ids)]}),
                    Command.create({'product_id': self.product_1.id, 'price_unit': 1000.0, 'tax_ids': [Command.set(self.tax10_goods.ids)]}),
                ],
            },
            {
                'move_type': 'out_invoice',
                'invoice_date': '2019-02-03',
                'date': '2019-01-30',
                'partner_id': self.partner_b.id,  # Spanish customer
                'invoice_line_ids': [
                    Command.create({'product_id': self.product_1.id, 'price_unit': 100.0, 'tax_ids': [Command.set(self.tax21_goods.ids)]}),
                    Command.create({'product_id': self.product_1.id, 'price_unit': 200.0, 'tax_ids': [Command.set(self.tax21_services.ids)]}),
                    Command.create({'product_id': self.product_1.id, 'price_unit': 1000.0, 'tax_ids': [Command.set(self.tax10_goods.ids)]}),
                ],
            },
        ])
        invoices.action_post()

        previous_record_identifier = {
            'IDEmisorFactura': '59962470K',
            'NumSerieFactura': 'INV/2018/00001',
            'FechaExpedicionFactura': '01-01-2018',
            'Huella': 'FA5DC48A0640BEB02A05160FD30020D1EA67FC1B400800ECDD9FC785E137C864',
        }

        document0 = invoices[0]._l10n_es_edi_verifactu_create_document(
            previous_record_identifier=previous_record_identifier,
        )
        self.assertFalse(document0.errors)
        document1 = invoices[1]._l10n_es_edi_verifactu_create_document(
            cancellation=True, previous_record_identifier=document0.record_identifier,
        )
        self.assertFalse(document1.errors)
        document2 = invoices[2]._l10n_es_edi_verifactu_create_document(
            previous_record_identifier=document1.record_identifier,
        )
        self.assertFalse(document2.errors)
        documents = self.env['l10n_es_edi_verifactu.document'].browse([
            document0.id, document1.id, document2.id,
        ])

        with self._mock_zeep_registration_operation_certificate_issue():
            batch_dict, _info = documents._send_as_batch()
        self.assertEqual(batch_dict, self._json_file_to_dict('l10n_es_edi_verifactu/tests/files/test_multiple_invoices_with_predecessor.json'))

    def test_invoice_cancellation_1(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2019-01-30',
            'date': '2019-01-30',
            'partner_id': self.partner_b.id,  # Spanish customer
            'invoice_line_ids': [
                Command.create({'product_id': self.product_1.id, 'price_unit': 100.0, 'tax_ids': [Command.set(self.tax21_goods.ids)]}),
                Command.create({'product_id': self.product_1.id, 'price_unit': 200.0, 'tax_ids': [Command.set(self.tax21_services.ids)]}),
                Command.create({'product_id': self.product_1.id, 'price_unit': 1000.0, 'tax_ids': [Command.set(self.tax10_goods.ids)]}),
            ],
        })
        invoice.action_post()

        document = invoice._l10n_es_edi_verifactu_create_document(cancellation=True)
        self.assertFalse(document.errors)
        with self._mock_zeep_registration_operation_certificate_issue():
            batch_dict, _info = document._send_as_batch()
        self.assertEqual(batch_dict, self._json_file_to_dict('l10n_es_edi_verifactu/tests/files/test_invoice_cancellation_1.json'))

    def test_invoice_simplified_partner(self):
        simplified_partner = self.env.ref('l10n_es.partner_simplified')
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2019-01-30',
            'date': '2019-01-30',
            'partner_id': simplified_partner.id,
            'invoice_line_ids': [
                Command.create({'product_id': self.product_1.id, 'price_unit': 100.0, 'tax_ids': [Command.set(self.tax21_goods.ids)]}),
            ],
        })
        invoice.action_post()

        document = invoice._l10n_es_edi_verifactu_create_document()
        self.assertFalse(document.errors)
        with self._mock_zeep_registration_operation_certificate_issue():
            batch_dict, _info = document._send_as_batch()
        self.assertEqual(batch_dict, self._json_file_to_dict('l10n_es_edi_verifactu/tests/files/test_invoice_simplified_partner.json'))
