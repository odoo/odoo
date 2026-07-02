# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, fields, tools
from odoo.tests.common import tagged
from odoo.exceptions import UserError
from odoo.addons.account.tests.test_account_move_send import TestAccountMoveSendCommon
from odoo.addons.l10n_hu_edi.tests.common import L10nHuEdiTestCommon

import requests
from freezegun import freeze_time
import contextlib


@tagged('post_install_l10n', '-at_install', 'post_install')
class L10nHuEdiTestFlowsMocked(L10nHuEdiTestCommon, TestAccountMoveSendCommon):
    """ Test the Hungarian EDI flows using mocked data from the test servers. """
    @classmethod
    def setUpClass(cls):
        with freeze_time('2024-01-25T15:28:53Z'):
            super().setUpClass()

    def test_send_invoice_and_credit_note(self):
        with self.patch_post(), \
                freeze_time('2024-01-25T15:28:53Z'):
            invoice = self.create_invoice_simple()
            invoice.action_post()
            send_and_print = self.create_send_and_print(invoice, sending_methods=[])
            self.assertTrue(send_and_print.extra_edi_checkboxes and send_and_print.extra_edi_checkboxes.get('hu_nav_30', {}).get('checked'))
            self.assertFalse(invoice._l10n_hu_edi_check_invoices())
            send_and_print.action_send_and_print()
            self.assertRecordValues(invoice, [{'l10n_hu_edi_state': 'confirmed', 'l10n_hu_invoice_chain_index': -1}])

            credit_note = self.create_reversal(invoice)
            credit_note.action_post()
            send_and_print = self.create_send_and_print(credit_note, sending_methods=[])
            self.assertTrue(send_and_print.extra_edi_checkboxes and send_and_print.extra_edi_checkboxes.get('hu_nav_30', {}).get('checked'))
            self.assertFalse(credit_note._l10n_hu_edi_check_invoices())
            send_and_print.action_send_and_print()
            self.assertRecordValues(credit_note, [{'l10n_hu_edi_state': 'confirmed', 'l10n_hu_invoice_chain_index': 1}])

    def test_send_invoice_warning(self):
        with tools.file_open('l10n_hu_edi/tests/mocked_requests/queryTransactionStatus_response_warning.xml', 'r') as response_file:
            response_data = response_file.read()
        with self.patch_post({'queryTransactionStatus': response_data}), \
                freeze_time('2024-01-25T15:28:53Z'):
            invoice = self.create_invoice_simple()
            invoice.action_post()
            send_and_print = self.create_send_and_print(invoice, sending_methods=[])
            self.assertTrue(send_and_print.extra_edi_checkboxes and send_and_print.extra_edi_checkboxes.get('hu_nav_30', {}).get('checked'))
            self.assertFalse(invoice._l10n_hu_edi_check_invoices())
            send_and_print.action_send_and_print()
            self.assertRecordValues(invoice, [{'l10n_hu_edi_state': 'confirmed_warning', 'l10n_hu_invoice_chain_index': -1}])

    def test_send_invoice_error(self):
        with tools.file_open('l10n_hu_edi/tests/mocked_requests/queryTransactionStatus_response_error.xml', 'r') as response_file:
            response_data = response_file.read()
        with self.patch_post({'queryTransactionStatus': response_data}), \
                freeze_time('2024-01-25T15:28:53Z'):
            invoice = self.create_invoice_simple()
            invoice.action_post()
            send_and_print = self.create_send_and_print(invoice, sending_methods=[])
            self.assertTrue(send_and_print.extra_edi_checkboxes and send_and_print.extra_edi_checkboxes.get('hu_nav_30', {}).get('checked'))
            self.assertFalse(invoice._l10n_hu_edi_check_invoices())
            with contextlib.suppress(UserError):
                send_and_print.action_send_and_print()
            self.assertRecordValues(invoice, [{'l10n_hu_edi_state': 'rejected', 'l10n_hu_invoice_chain_index': 0}])

    def test_timeout_recovery_fail(self):
        with freeze_time('2024-01-25T15:28:53Z'), \
                self.patch_post({'manageInvoice': requests.Timeout()}):
            invoice = self.create_invoice_simple()
            invoice.action_post()

            send_and_print = self.create_send_and_print(invoice, sending_methods=[])
            self.assertTrue(send_and_print.extra_edi_checkboxes and send_and_print.extra_edi_checkboxes.get('hu_nav_30', {}).get('checked'))
            self.assertFalse(invoice._l10n_hu_edi_check_invoices())
            send_and_print.action_send_and_print()
            self.assertRecordValues(invoice, [{'l10n_hu_edi_state': 'send_timeout', 'l10n_hu_invoice_chain_index': -1}])

        with tools.file_open('l10n_hu_edi/tests/mocked_requests/queryTransactionStatus_response_original.xml', 'r') as response_file:
            response_data = response_file.read()
        # Advance 10 minutes so the timeout recovery mechanism triggers.
        with freeze_time('2024-01-25T15:38:53Z'), \
                self.patch_post({'queryTransactionStatus': response_data}):
            with contextlib.suppress(UserError):
                invoice.l10n_hu_edi_button_update_status()
            self.assertRecordValues(invoice, [{'l10n_hu_edi_state': 'rejected', 'l10n_hu_invoice_chain_index': 0}])

    def test_timeout_recovery_success(self):
        with freeze_time('2024-01-25T15:28:53Z'), \
                self.patch_post({'manageInvoice': requests.Timeout()}):
            invoice = self.create_invoice_simple()
            invoice.name = 'INV/2024/00999'  # This matches the invoice name in the XML returned by queryTransactionStatus.
            invoice.action_post()

            send_and_print = self.create_send_and_print(invoice, sending_methods=[])
            self.assertTrue(send_and_print.extra_edi_checkboxes and send_and_print.extra_edi_checkboxes.get('hu_nav_30', {}).get('checked'))
            self.assertFalse(invoice._l10n_hu_edi_check_invoices())
            send_and_print.action_send_and_print()
            self.assertRecordValues(invoice, [{'l10n_hu_edi_state': 'send_timeout', 'l10n_hu_invoice_chain_index': -1}])

        # This returns an original XML with name INV/2024/00999
        with tools.file_open('l10n_hu_edi/tests/mocked_requests/queryTransactionStatus_response_original.xml', 'r') as response_file:
            response_data = response_file.read()

        # Advance 10 minutes so the timeout recovery mechanism triggers.
        with freeze_time('2024-01-25T15:38:53Z'), \
                self.patch_post({'queryTransactionStatus': response_data}):
            invoice.l10n_hu_edi_button_update_status()
            self.assertRecordValues(invoice, [{'l10n_hu_edi_state': 'confirmed', 'l10n_hu_invoice_chain_index': -1}])

    def test_cancel_invoice_error(self):
        with freeze_time('2024-01-25T15:28:53Z'):
            with self.patch_post():
                invoice, cancel_wizard = self.create_cancel_wizard()
                self.assertRecordValues(invoice, [{'l10n_hu_edi_state': 'confirmed'}])
            with tools.file_open('l10n_hu_edi/tests/mocked_requests/queryTransactionStatus_response_error.xml', 'r') as response_file:
                response_data = response_file.read()
            with self.patch_post({'queryTransactionStatus': response_data}):
                with contextlib.suppress(UserError):
                    cancel_wizard.button_request_cancel()
                self.assertRecordValues(invoice, [{'l10n_hu_edi_state': 'confirmed_warning', 'l10n_hu_invoice_chain_index': -1}])

    def test_cancel_invoice_pending(self):
        with freeze_time('2024-01-25T15:28:53Z'):
            with self.patch_post():
                invoice, cancel_wizard = self.create_cancel_wizard()
                self.assertRecordValues(invoice, [{'l10n_hu_edi_state': 'confirmed'}])
            with tools.file_open('l10n_hu_edi/tests/mocked_requests/queryTransactionStatus_response_annulment_pending.xml', 'r') as response_file:
                response_data = response_file.read()
            with self.patch_post({'queryTransactionStatus': response_data}):
                cancel_wizard.button_request_cancel()
                self.assertRecordValues(invoice, [{'l10n_hu_edi_state': 'cancel_pending', 'l10n_hu_invoice_chain_index': -1}])

    def test_cancel_invoice_done(self):
        with freeze_time('2024-01-25T15:28:53Z'):
            with self.patch_post():
                invoice, cancel_wizard = self.create_cancel_wizard()
                self.assertRecordValues(invoice, [{'l10n_hu_edi_state': 'confirmed', 'l10n_hu_invoice_chain_index': -1}])
            with tools.file_open('l10n_hu_edi/tests/mocked_requests/queryTransactionStatus_response_annulment_done.xml', 'r') as response_file:
                response_data = response_file.read()
            with self.patch_post({'queryTransactionStatus': response_data}):
                cancel_wizard.button_request_cancel()
                self.assertRecordValues(invoice, [{'l10n_hu_edi_state': 'cancelled', 'state': 'cancel', 'l10n_hu_invoice_chain_index': 0}])

    def test_cancel_and_resend(self):
        """ Test the sending, annulment and re-sending of an invoice + credit note + modif. invoice """
        with freeze_time('2024-01-25T15:28:53Z'):
            with self.patch_post():
                invoice, cancel_wizard = self.create_cancel_wizard()
                self.assertRecordValues(invoice, [{'l10n_hu_edi_state': 'confirmed', 'l10n_hu_invoice_chain_index': -1}])

                new_invoice = self.create_reversal(invoice, is_modify=True)
                self.assertRecordValues(new_invoice, [{'debit_origin_id': invoice.id}])
                new_invoice.action_post()
                credit_note = invoice.reversal_move_ids

                send_and_print = self.create_send_and_print(credit_note, sending_methods=[])
                self.assertTrue(send_and_print.extra_edi_checkboxes and send_and_print.extra_edi_checkboxes.get('hu_nav_30', {}).get('checked'))
                self.assertFalse(credit_note._l10n_hu_edi_check_invoices())
                send_and_print.action_send_and_print()
                self.assertRecordValues(credit_note, [{'l10n_hu_edi_state': 'confirmed', 'l10n_hu_invoice_chain_index': 1}])

                send_and_print = self.create_send_and_print(new_invoice, sending_methods=[])
                self.assertTrue(send_and_print.extra_edi_checkboxes and send_and_print.extra_edi_checkboxes.get('hu_nav_30', {}).get('checked'))
                self.assertFalse(new_invoice._l10n_hu_edi_check_invoices())
                send_and_print.action_send_and_print()
                self.assertRecordValues(new_invoice, [{'l10n_hu_edi_state': 'confirmed', 'l10n_hu_invoice_chain_index': 2}])

            with tools.file_open('l10n_hu_edi/tests/mocked_requests/queryTransactionStatus_response_annulment_done.xml', 'r') as response_file:
                response_data = response_file.read()
            with self.patch_post({'queryTransactionStatus': response_data}):
                cancel_wizard.button_request_cancel()
                self.assertRecordValues(invoice, [{'l10n_hu_edi_state': 'cancelled', 'state': 'cancel', 'l10n_hu_invoice_chain_index': 0}])
                self.assertRecordValues(credit_note, [{'l10n_hu_edi_state': 'cancelled', 'state': 'cancel', 'l10n_hu_invoice_chain_index': 0}])
                self.assertRecordValues(new_invoice, [{'l10n_hu_edi_state': 'cancelled', 'state': 'cancel', 'l10n_hu_invoice_chain_index': 0}])

            (invoice | credit_note | new_invoice).button_draft()
            invoice.action_post()
            credit_note.action_post()
            new_invoice.action_post()

            with self.patch_post():
                send_and_print = self.create_send_and_print(invoice, sending_methods=[])
                self.assertTrue(send_and_print.extra_edi_checkboxes and send_and_print.extra_edi_checkboxes.get('hu_nav_30', {}).get('checked'))
                self.assertFalse(invoice._l10n_hu_edi_check_invoices())
                send_and_print.action_send_and_print()
                self.assertRecordValues(invoice, [{'l10n_hu_edi_state': 'confirmed', 'l10n_hu_invoice_chain_index': -1}])

                send_and_print = self.create_send_and_print(credit_note, sending_methods=[])
                self.assertTrue(send_and_print.extra_edi_checkboxes and send_and_print.extra_edi_checkboxes.get('hu_nav_30', {}).get('checked'))
                self.assertFalse(credit_note._l10n_hu_edi_check_invoices())
                send_and_print.action_send_and_print()
                self.assertRecordValues(credit_note, [{'l10n_hu_edi_state': 'confirmed', 'l10n_hu_invoice_chain_index': 1}])

                send_and_print = self.create_send_and_print(new_invoice, sending_methods=[])
                self.assertTrue(send_and_print.extra_edi_checkboxes and send_and_print.extra_edi_checkboxes.get('hu_nav_30', {}).get('checked'))
                self.assertFalse(new_invoice._l10n_hu_edi_check_invoices())
                send_and_print.action_send_and_print()
                self.assertRecordValues(new_invoice, [{'l10n_hu_edi_state': 'confirmed', 'l10n_hu_invoice_chain_index': 2}])

    def test_invoice_line_currency_rate_from_sale(self):
        if self.env['ir.module.module']._get('sale_stock').state == 'installed':
            self.env.user.group_ids += self.env.ref('sales_team.group_sale_salesman')
            currency = self.setup_other_currency('HRK', rates=[
                ('2015-12-31', 3.0),
                ('2016-12-31', 2.0),
            ])
            pricelist = self.env['product.pricelist'].create({
                'name': 'Foreign pricelist',
                'currency_id': currency.id,
            })

            sale_order = self.env['sale.order'].create({
                'partner_id': self.partner_company.id,
                'partner_invoice_id': self.partner_company.id,
                'pricelist_id': pricelist.id,
                'order_line': [Command.create({
                    'product_id': self.product.id,
                    'product_uom_qty': 1,
                    'price_unit': 600,
                })],
                'currency_id': currency.id,
                'date_order': '2017-01-01',
            })
            sale_order.action_confirm()

            delivery = sale_order.picking_ids
            delivery.button_validate()
            delivery.date_done = '2016-01-01'

            invoice = sale_order._create_invoices()
            self.assertRecordValues(invoice.line_ids, [
                {'amount_currency': -600.00,   'balance': -200.00},
                {'amount_currency': -162.00,   'balance': -54.00},
                {'amount_currency': 762.00,    'balance': 254.00},
            ])

    def test_case_1_invoice_payment_storno(self):
        inv = self.create_invoice_simple(amount=1000)
        inv.action_post()
        operation = inv._l10n_hu_edi_get_operation_type()
        self.assertEqual(operation, 'CREATE')
        self.register_payment(inv, 1000)
        self.create_reversal(inv, is_modify=True)
        operation = inv.reversal_move_ids._l10n_hu_edi_get_operation_type()
        self.assertEqual(operation, 'STORNO')

    def test_case_2_modify_then_storno(self):
        inv = self.create_invoice_simple(amount=1000)
        inv.action_post()
        operation = inv._l10n_hu_edi_get_operation_type()
        self.assertEqual(operation, 'CREATE')
        mod1 = self.create_reversal(inv, amount=100)
        mod1.action_post()
        operation = mod1._l10n_hu_edi_get_operation_type()
        self.assertEqual(operation, 'MODIFY')
        storno = self.create_reversal(inv, amount=900)
        storno.action_post()
        operation = storno._l10n_hu_edi_get_operation_type()
        self.assertEqual(operation, 'STORNO')

    def test_case_3_multiple_modifications_then_storno(self):
        inv = self.create_invoice_simple(amount=1000)
        inv.action_post()
        operation = inv._l10n_hu_edi_get_operation_type()
        self.assertEqual(operation, 'CREATE')
        mod1 = self.create_reversal(inv, amount=100)
        mod1.action_post()
        operation = mod1._l10n_hu_edi_get_operation_type()
        self.assertEqual(operation, 'MODIFY')
        mod2 = self.create_reversal(inv, amount=100)
        mod2.action_post()
        operation = mod2._l10n_hu_edi_get_operation_type()
        self.assertEqual(operation, 'MODIFY')
        storno = self.create_reversal(inv, amount=800)
        storno.action_post()
        operation = storno._l10n_hu_edi_get_operation_type()
        self.assertEqual(operation, 'STORNO')

    def test_case_4_modification_payment_then_storno(self):
        inv = self.create_invoice_simple(amount=1000)
        inv.action_post()
        operation = inv._l10n_hu_edi_get_operation_type()
        self.assertEqual(operation, 'CREATE')
        mod1 = self.create_reversal(inv, amount=100)
        mod1.action_post()
        operation = mod1._l10n_hu_edi_get_operation_type()
        self.assertEqual(operation, 'MODIFY')
        self.register_payment(inv, 900)
        self.create_reversal(inv, is_modify=True)
        mod2 = inv.reversal_move_ids
        mod2.button_draft()
        mod2.invoice_line_ids[0].write({
            'price_unit': 900,
        })
        mod2.action_post()
        # Reconcile the outstanding payment line from mod1 with the invoice
        inv.js_assign_outstanding_line(mod1.line_ids.filtered(lambda l: l.debit == 0).id)
        operation = mod2._l10n_hu_edi_get_operation_type()
        self.assertEqual(operation, 'STORNO')

    def test_case_5_debit_note_then_storno(self):
        inv = self.create_invoice_simple(amount=1000)
        inv.action_post()
        operation = inv._l10n_hu_edi_get_operation_type()
        self.assertEqual(operation, 'CREATE')
        dn = self.create_debit_note(inv, amount=100)
        dn.action_post()
        operation = dn._l10n_hu_edi_get_operation_type()
        self.assertEqual(operation, 'MODIFY')
        storno = self.create_reversal(inv, amount=1100)
        storno.action_post()
        # Reconcile the outstanding payment line from dn with the storno
        storno.js_assign_outstanding_line(dn.line_ids.filtered(lambda l: l.credit == 0).id)
        operation = storno._l10n_hu_edi_get_operation_type()
        self.assertEqual(operation, 'STORNO')

    def test_fetching_bills_from_nav(self):
        wizard = self.env['l10n_hu_edi.receive.bills.wizard'].create({})
        with self.patch_post():
            action = wizard.action_receive_bills()
        moves = self.env['account.move'].search(action['params']['next']['domain'])

        self.assertRecordValues(moves, [
            {
                'move_type': 'in_refund',
                'ref': 'BATCH_MOD_2026_0002-2',
                'invoice_date': fields.Date.from_string('2026-02-01'),
                'delivery_date': fields.Date.from_string('2026-01-22'),
                'invoice_date_due': fields.Date.from_string('2026-01-22'),
                'currency_id': self.currency_huf.id,
                'invoice_currency_rate': 1.00,
                'l10n_hu_invoice_chain_index': 1,
                'l10n_hu_payment_mode': False,
                'amount_untaxed': 235.00,
                'amount_tax': 63.45,
                'amount_total': 298.45,
                'l10n_hu_edi_transaction_code': '59BG5EQ2PKD9KXZM',
                'l10n_hu_edi_batch_upload_index': 1,
                'l10n_hu_edi_send_time': fields.Datetime.from_string('2026-01-22 17:21:55'),
                'partner_bank_id': self.company.partner_id.bank_ids.id,
            },
            {
                'move_type': 'in_refund',
                'ref': 'BATCH_MOD_2026_0002-1',
                'invoice_date': fields.Date.from_string('2026-02-01'),
                'delivery_date': fields.Date.from_string('2026-01-22'),
                'invoice_date_due': fields.Date.from_string('2026-01-22'),
                'currency_id': self.currency_huf.id,
                'invoice_currency_rate': 1.00,
                'l10n_hu_invoice_chain_index': 1,
                'l10n_hu_payment_mode': False,
                'amount_untaxed': 735.00,
                'amount_tax': 36.75,
                'amount_total': 771.75,
                'l10n_hu_edi_transaction_code': '59BG5EQ2PKD9KXZM',
                'l10n_hu_edi_batch_upload_index': 1,
                'l10n_hu_edi_send_time': fields.Datetime.from_string('2026-01-22 17:21:55'),
                'partner_bank_id': self.company.partner_id.bank_ids.id,
            },
            {
                'move_type': 'in_invoice',
                'ref': 'INV/2026/00004',
                'invoice_date': fields.Date.from_string('2026-01-22'),
                'delivery_date': fields.Date.from_string('2026-01-22'),
                'invoice_date_due': fields.Date.from_string('2026-01-22'),
                'currency_id': self.currency_huf.id,
                'invoice_currency_rate': 1.00,
                'l10n_hu_invoice_chain_index': -1,
                'l10n_hu_payment_mode': False,
                'amount_untaxed': 235.00,
                'amount_tax': 63.45,
                'amount_total': 298.45,
                'l10n_hu_edi_transaction_code': '59BFCJN2FHW8OIGG',
                'l10n_hu_edi_batch_upload_index': 2,
                'l10n_hu_edi_send_time': fields.Datetime.from_string('2026-01-22 16:59:29'),
                'partner_bank_id': moves.partner_id.bank_ids.id,
            },
            {
                'move_type': 'in_invoice',
                'ref': 'INV/2026/00003',
                'invoice_date': fields.Date.from_string('2026-01-22'),
                'delivery_date': fields.Date.from_string('2026-01-22'),
                'invoice_date_due': fields.Date.from_string('2026-01-22'),
                'currency_id': self.currency_huf.id,
                'invoice_currency_rate': 1.00,
                'l10n_hu_invoice_chain_index': -1,
                'l10n_hu_payment_mode': False,
                'amount_untaxed': 735.00,
                'amount_tax': 36.75,
                'amount_total': 771.75,
                'l10n_hu_edi_transaction_code': '59BFCJN2FHW8OIGG',
                'l10n_hu_edi_batch_upload_index': 1,
                'l10n_hu_edi_send_time': fields.Datetime.from_string('2026-01-22 16:59:29'),
                'partner_bank_id': moves.partner_id.bank_ids.id,
            },
        ])

        self.assertRecordValues(moves[0].invoice_line_ids, [{
            'name': 'Correction – [E-COM10] Pedal Bin',
            'quantity': 5.00,
            'price_unit': 47.00,
            'discount': 0.00,
            'tax_ids': self.tax_purchase_27.ids,
        }])
        self.assertRecordValues(moves[1].invoice_line_ids, [{
            'name': 'Correction – [E-COM06] Corner Desk Right Sit',
            'quantity': 5.00,
            'price_unit': 147.00,
            'discount': 0.00,
            'tax_ids': self.tax_purchase_5.ids,
        }])
        self.assertRecordValues(moves[2].invoice_line_ids, [{
            'name': '[E-COM10] Pedal Bin',
            'quantity': 5.00,
            'price_unit': 47.00,
            'discount': 0.00,
            'tax_ids': self.tax_purchase_27.ids,
        }])
        self.assertRecordValues(moves[3].invoice_line_ids, [{
            'name': '[E-COM06] Corner Desk Right Sit',
            'quantity': 5.00,
            'price_unit': 147.00,
            'discount': 0.00,
            'tax_ids': self.tax_purchase_5.ids,
        }])
        self.assertRecordValues(moves.partner_id, [{
            'name': 'Goodo Systems Kft.',
            'vat': '27470217-2-42',
            'l10n_hu_group_vat': False,
        }])

        self.assertRecordValues(moves.partner_id.bank_ids, [{
            'account_number': 'HU55 1070 0024 7733 4423 2787 4189',
            'holder_name': 'Goodo Systems Kft.',
        }])
        self.assertRecordValues(self.company.partner_id.bank_ids, [{
            'account_number': 'HU55 1070 0024 7733 4423 2787 4189',
            'holder_name': 'company_1_data',
        }])

        move_count_before = self.env['account.move'].search_count([])
        with self.patch_post():
            action = wizard.action_receive_bills()
        moves_count_after = self.env['account.move'].search_count([])
        self.assertEqual(move_count_before, moves_count_after, "No new moves should be created when fetching the same bills again.")
