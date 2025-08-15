import datetime

from contextlib import contextmanager, nullcontext
from freezegun import freeze_time
from unittest import mock

from odoo.addons.point_of_sale.models.pos_order import PosOrder
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import TestL10nEsEdiVerifactuPosCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nEsEdiVerifactuPosOrder(TestL10nEsEdiVerifactuPosCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.config = cls.basic_config

        # Ensure the date of all orders is in the past.
        # Else the associated move does not get posted (since it will be in the future / on the order date).
        cls.fakenow = datetime.datetime(2025, 1, 1)
        cls.startClassPatcher(freeze_time(cls.fakenow))
        # `freeze_time` does not change the `create_date`
        cls.startClassPatcher(cls._mock_create_date(cls, '2025-01-01'))

    @contextmanager
    def with_pos_session(self):
        session = self.open_new_session(0.0)
        yield session
        session.post_closing_cash_details(0.0)
        session.close_session_from_ui()

    def _create_order(self, data):
        date_order = data.pop('date_order', None)
        name = data.pop('name', None)
        account_move = data.pop('account_move', None)

        order_data = self.create_ui_order_data(**data)

        # In case the Veri*Factu document is created for the pos order:
        # We have to fix the record identifier related fields on the order
        if date_order:
            order_data['data']['date_order'] = date_order
        name_patch = nullcontext()
        if name:
            name_function_path = 'odoo.addons.point_of_sale.models.pos_order.PosOrder._compute_order_name'
            name_patch = mock.patch(name_function_path, return_value=name)

        # In case the Veri*Factu document is created for the invoice of the pos order:
        # We have to fix the record identifier related fields on the created invoice
        prepare_invoice_vals_patch = nullcontext()
        if account_move:
            prepare_invoice_vals_function_path = 'odoo.addons.point_of_sale.models.pos_order.PosOrder._prepare_invoice_vals'
            original_prepare_invoice_vals = PosOrder._prepare_invoice_vals

            def _patched_prepare_invoice_vals(self):
                vals = original_prepare_invoice_vals(self)

                name = account_move.get('name')
                date = account_move.get('date')  # to match the 'name'
                invoice_date = account_move.get('invoice_date')
                if name:
                    vals['name'] = name
                if date:
                    vals['date'] = date
                if invoice_date:
                    vals['invoice_date'] = invoice_date

                return vals

            prepare_invoice_vals_patch = mock.patch(prepare_invoice_vals_function_path, _patched_prepare_invoice_vals)

        with name_patch, prepare_invoice_vals_patch:
            results = self.env['pos.order'].create_from_ui([order_data])
        return self.env['pos.order'].browse(results[0]['id'])

    def test_record_identifier(self):
        with self.with_pos_session():
            with self._mock_zeep_registration_operation_certificate_issue():
                order = self._create_order({
                    'pos_order_lines_ui_args': [
                        (self.product, 1.0),
                    ],
                    'payments': [(self.bank_pm1, 121.0)],
                    # Adjust the fields relevant for the record identifier to match the ones in the response
                    'name': 'INV/2019/00004',
                    'date_order': '2024-11-10 10:11:12',
                })

            # Check that `_create_order` sets the 'name' and 'date_order' correctly
            self.assertRecordValues(order, [{
                'name': 'INV/2019/00004',
                'date_order': datetime.datetime(2024, 11, 10, 10, 11, 12),
               }])

            self.assertEqual(len(order.l10n_es_edi_verifactu_document_ids), 1)

            expected_record_identifier = {
                'IDEmisorFactura': 'A39200019',
                'NumSerieFactura': 'INV/2019/00004',
                'FechaExpedicionFactura': '2024-11-10',
               }
            record_identifier = order.l10n_es_edi_verifactu_document_ids._get_record_identifier()
            self.assertDictEqual(record_identifier, expected_record_identifier | record_identifier)

    def test_error_above_simplified_limit(self):
        with self.with_pos_session():
            with self.assertRaisesRegex(UserError, "The order needs to be invoiced since its total amount is above 400€."), \
                 mute_logger('odoo.addons.point_of_sale.models.pos_order'):
                self._create_order({
                    'pos_order_lines_ui_args': [
                        (self.product, 10.0),
                    ],
                    'payments': [(self.bank_pm1, 1210.0)],
                })

    def test_order_not_invoiced(self):
        with self.with_pos_session():
            with self._mock_zeep_registration_operation('l10n_es_edi_verifactu/tests/responses/batch_single_accepted_registration.json'):
                order = self._create_order({
                    'pos_order_lines_ui_args': [
                        (self.product, 1.0),
                    ],
                    'payments': [(self.bank_pm1, 121.0)],
                    # Adjust the fields relevant for the record identifier to match the ones in the response
                    'name': 'INV/2019/00026',
                    'date_order': '2024-12-30 00:00:00',
                })
            with self._mock_zeep_registration_operation_certificate_issue():
                refund_action = order.refund()
                refund = self.env['pos.order'].browse(refund_action['res_id'])
                payment_context = {"active_ids": refund.ids, "active_id": refund.id}
                refund_payment = self.env['pos.make.payment'].with_context(**payment_context).create({
                    'amount': refund.amount_total,
                    'payment_method_id': self.bank_pm1.id,
                })
                refund.l10n_es_edi_verifactu_refund_reason = 'R5'
                refund_payment.with_context(**payment_context).check()
                self.pos_session.action_pos_session_validate()

        self.assertRecordValues(order, [{
            'l10n_es_edi_verifactu_state': 'accepted',
            'l10n_es_edi_verifactu_qr_code': '/report/barcode/?barcode_type=QR&value=https%3A%2F%2Fprewww2.aeat.es%2Fwlpl%2FTIKE-CONT%2FValidarQR%3Fnif%3DA39200019%26numserie%3DINV%252F2019%252F00026%26fecha%3D30-12-2024%26importe%3D121.00&barLevel=M&width=180&height=180',
        }])

        order_document = order.l10n_es_edi_verifactu_document_ids
        refund_document = refund.l10n_es_edi_verifactu_document_ids
        self.assertRecordValues((order_document + refund_document), [
            {
                'pos_order_id': order.id,
                'move_id': False,
                'document_type': 'submission',
                'response_csv': 'A-YDSW8NLFLANWPM',
                'state': 'accepted',
                'errors': False,
            },
            {
                'pos_order_id': refund.id,
                'move_id': False,
                'document_type': 'submission',
                'response_csv': False,
                'state': False,
                'errors': False,
            }
        ])

        self.assertEqual(order_document._get_document_dict(),
                         self._json_file_to_dict('l10n_es_edi_verifactu_pos/tests/files/test_order_not_invoiced_order.json'))

        self.assertEqual(refund_document._get_document_dict(),
                         self._json_file_to_dict('l10n_es_edi_verifactu_pos/tests/files/test_order_not_invoiced_refund.json'))

    def test_order_invoiced_simplified(self):
        with self.with_pos_session():
            with self._mock_zeep_registration_operation('l10n_es_edi_verifactu/tests/responses/batch_single_accepted_registration.json'):
                order = self._create_order({
                    # Note: The total is not above the simplified invoice limit
                    'is_invoiced': True,
                    'customer': self.partner_b,  # Spanish customer
                    'pos_order_lines_ui_args': [
                        (self.product, 1.0),
                    ],
                    'payments': [(self.bank_pm1, 121.0)],
                    'account_move': {
                        # Adjust the fields relevant for the record identifier to match the ones in the response
                        'name': 'INV/2019/00026',
                        'date': '2019-12-30',
                        'invoice_date': '2024-12-30',
                    }
                })
        # Check that the created invoice is not simplified
        invoice = order.account_move
        self.assertTrue(invoice)
        self.assertRecordValues(invoice, [{
            'partner_id': self.partner_b.id,
            'l10n_es_is_simplified': False,
        }])

        # The Veri*Factu document was created for the invoice and not the document
        self.assertRecordValues(invoice.l10n_es_edi_verifactu_document_ids, [{
            'pos_order_id': False,
            'move_id': invoice.id,
            'document_type': 'submission',
            'response_csv': 'A-YDSW8NLFLANWPM',
            'state': 'accepted',
            'errors': False,
        }])

    def test_order_invoiced_not_simplified(self):
        with self.with_pos_session():
            with self._mock_zeep_registration_operation('l10n_es_edi_verifactu/tests/responses/batch_single_accepted_registration.json'):
                order = self._create_order({
                    # Note: The total is above the simplified invoice limit
                    'is_invoiced': True,
                    'customer': self.partner_b,  # Spanish customer
                    'pos_order_lines_ui_args': [
                        (self.product, 10.0),
                    ],
                    'payments': [(self.bank_pm1, 1210.0)],
                    'account_move': {
                        # Adjust the fields relevant for the record identifier to match the ones in the response
                        'name': 'INV/2019/00026',
                        'date': '2019-12-30',
                        'invoice_date': '2024-12-30',
                    }
                })

        # The Veri*Factu document was created for the invoice and not the document
        invoice = order.account_move
        self.assertRecordValues(order, [{
            'l10n_es_edi_verifactu_document_ids': [],
            'l10n_es_edi_verifactu_qr_code': invoice.l10n_es_edi_verifactu_qr_code,
        }])
        self.assertRecordValues(invoice.l10n_es_edi_verifactu_document_ids, [{
            'pos_order_id': False,
            'move_id': invoice.id,
            'document_type': 'submission',
            'response_csv': 'A-YDSW8NLFLANWPM',
            'state': 'accepted',
            'errors': False,
        }])
