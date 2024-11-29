# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.account_check_printing.models.account_payment import INV_LINES_PER_STUB
from odoo.tests import tagged
from odoo.tools.misc import NON_BREAKING_SPACE
from odoo import Command

import math


@tagged('post_install', '-at_install')
class TestPrintCheck(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.other_currency = cls.setup_other_currency('EUR')

        bank_journal = cls.company_data['default_journal_bank']

        cls.payment_method_line_check = bank_journal.outbound_payment_method_line_ids\
            .filtered(lambda l: l.code == 'check_printing')
        cls.payment_method_line_check.payment_account_id = cls.inbound_payment_method_line.payment_account_id

    def test_in_invoice_check_manual_sequencing(self):
        ''' Test the check generation for vendor bills. '''
        nb_invoices_to_test = INV_LINES_PER_STUB + 1

        self.company_data['default_journal_bank'].write({
            'check_manual_sequencing': True,
            'check_next_number': '00042',
        })

        # Create 10 customer invoices.
        in_invoices = self.env['account.move'].create([{
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 100.0,
                'tax_ids': []
            })]
        } for i in range(nb_invoices_to_test)])
        in_invoices.action_post()

        # Create a single payment.
        payment = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=in_invoices.ids).create({
            'group_payment': True,
            'payment_method_line_id': self.payment_method_line_check.id,
        })._create_payments()

        # Check created payment.
        self.assertRecordValues(payment, [{
            'payment_method_line_id': self.payment_method_line_check.id,
            'check_amount_in_words': payment.currency_id.amount_to_text(100.0 * nb_invoices_to_test),
            'check_number': '00042',
        }])

        # Check pages.
        self.company_data['company'].account_check_printing_multi_stub = True
        report_pages = payment._check_get_pages()
        self.assertEqual(len(report_pages), int(math.ceil(len(in_invoices) / INV_LINES_PER_STUB)))

        self.company_data['company'].account_check_printing_multi_stub = False
        report_pages = payment._check_get_pages()
        self.assertEqual(len(report_pages), 1)

    def test_out_refund_check_manual_sequencing(self):
        ''' Test the check generation for refunds. '''
        nb_invoices_to_test = INV_LINES_PER_STUB + 1

        self.company_data['default_journal_bank'].write({
            'check_manual_sequencing': True,
            'check_next_number': '00042',
        })

        # Create 10 refunds.
        out_refunds = self.env['account.move'].create([{
            'move_type': 'out_refund',
            'partner_id': self.partner_a.id,
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 100.0,
                'tax_ids': []
            })]
        } for i in range(nb_invoices_to_test)])
        out_refunds.action_post()

        # Create a single payment.
        payment = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=out_refunds.ids).create({
            'group_payment': True,
            'payment_method_line_id': self.payment_method_line_check.id,
        })._create_payments()

        # Check created payment.
        self.assertRecordValues(payment, [{
            'payment_method_line_id': self.payment_method_line_check.id,
            'check_amount_in_words': payment.currency_id.amount_to_text(100.0 * nb_invoices_to_test),
            'check_number': '00042',
        }])

        # Check pages.
        self.company_data['company'].account_check_printing_multi_stub = True
        report_pages = payment._check_get_pages()
        self.assertEqual(len(report_pages), int(math.ceil(len(out_refunds) / INV_LINES_PER_STUB)))

        self.company_data['company'].account_check_printing_multi_stub = False
        report_pages = payment._check_get_pages()
        self.assertEqual(len(report_pages), 1)

    def test_multi_currency_stub_lines(self):
        # Invoice in company's currency: 100$
        invoice = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'date': '2016-01-01',
            'invoice_date': '2016-01-01',
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 150.0,
                'tax_ids': []
            })]
        })
        invoice.action_post()

        # Partial payment in foreign currency.
        payment = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=invoice.ids).create({
            'payment_method_line_id': self.payment_method_line_check.id,
            'currency_id': self.other_currency.id,
            'amount': 150.0,
            'payment_date': '2017-01-01',
        })._create_payments()

        stub_pages = payment._check_make_stub_pages()

        self.assertEqual(stub_pages, [[{
            'due_date': '01/01/2016',
            'number': invoice.name,
            'amount_total': f'${NON_BREAKING_SPACE}150.00',
            'amount_residual': f'${NON_BREAKING_SPACE}75.00',
            'amount_paid': f'150.00{NON_BREAKING_SPACE}€',
            'currency': invoice.currency_id,
        }]])

    def test_in_invoice_check_manual_sequencing_with_multiple_payments(self):
        """
           Test the check generation for vendor bills with multiple payments.
        """
        nb_invoices_to_test = INV_LINES_PER_STUB + 1

        self.company_data['default_journal_bank'].write({
            'check_manual_sequencing': True,
            'check_next_number': '11111',
        })

        in_invoices = self.env['account.move'].create([{
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 100.0,
                'tax_ids': []
            })]
        } for i in range(nb_invoices_to_test)])
        in_invoices.action_post()

        payments = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=in_invoices.ids).create({
            'group_payment': False,
            'payment_method_line_id': self.payment_method_line_check.id,
        })._create_payments()

        self.assertEqual(set(payments.mapped('check_number')), {str(x) for x in range(11111, 11111 + nb_invoices_to_test)})

    def test_check_label(self):
        payment = self.env['account.payment'].create({
            'check_number': '2147483647',
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'amount': 100.0,
            'journal_id': self.company_data['default_journal_bank'].id,
            'payment_method_line_id': self.payment_method_line_check.id,
        })
        payment.action_post()

        for move in payment.move_id:
            self.assertRecordValues(move.line_ids, [{'name': "Checks - 2147483647"}] * len(move.line_ids))

    def test_print_great_pre_number_check(self):
        """
        Make sure we can use integer of more than 2147483647 in check sequence
         limit of `integer` type in psql: https://www.postgresql.org/docs/current/datatype-numeric.html
        """
        vals = {
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'amount': 100.0,
            'journal_id': self.company_data['default_journal_bank'].id,
            'payment_method_line_id': self.payment_method_line_check.id,
        }
        payment = self.env['account.payment'].create(vals)
        payment.action_post()
        self.assertTrue(payment.write({'check_number': '2147483647'}))
        self.assertTrue(payment.write({'check_number': '2147483648'}))

        payment_2 = self.env['account.payment'].create(vals)
        payment_2.action_post()
        action_window = payment_2.print_checks()
        self.assertEqual(action_window['context']['default_next_check_number'], '2147483649', "Check number should have been incremented without error.")
