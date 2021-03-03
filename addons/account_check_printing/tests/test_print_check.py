# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.account_check_printing.models.account_payment import INV_LINES_PER_STUB
from odoo.tests import tagged

import math


@tagged('post_install', '-at_install')
class TestPrintCheck(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.payment_method_check = cls.env.ref("account_check_printing.account_payment_method_check")

        cls.company_data['default_journal_bank'].write({
            'outbound_payment_method_ids': [(6, 0, (
                cls.env.ref('account.account_payment_method_manual_out').id,
                cls.payment_method_check.id,
            ))],
        })

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
            'invoice_line_ids': [(0, 0, {'product_id': self.product_a.id, 'price_unit': 100.0})]
        } for i in range(nb_invoices_to_test)])
        in_invoices.action_post()

        # Create a single payment.
        payment = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=in_invoices.ids).create({
            'group_payment': True,
            'payment_method_id': self.payment_method_check.id,
        })._create_payments()

        # Check created payment.
        self.assertRecordValues(payment, [{
            'payment_method_id': self.payment_method_check.id,
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
            'invoice_line_ids': [(0, 0, {'product_id': self.product_a.id, 'price_unit': 100.0})]
        } for i in range(nb_invoices_to_test)])
        out_refunds.action_post()

        # Create a single payment.
        payment = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=out_refunds.ids).create({
            'group_payment': True,
            'payment_method_id': self.payment_method_check.id,
        })._create_payments()

        # Check created payment.
        self.assertRecordValues(payment, [{
            'payment_method_id': self.payment_method_check.id,
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
            'invoice_line_ids': [(0, 0, {'product_id': self.product_a.id, 'price_unit': 100.0})]
        })
        invoice.action_post()

        # Partial payment in foreign currency: 100Gol = 33.33$.
        payment = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=invoice.ids).create({
            'payment_method_id': self.payment_method_check.id,
            'currency_id': self.currency_data['currency'].id,
            'amount': 100.0,
            'payment_date': '2017-01-01',
        })._create_payments()

        stub_pages = payment._check_make_stub_pages()

        self.assertEqual(stub_pages, [[{
            'due_date': '01/01/2016',
            'number': invoice.name,
            'amount_total': '$ 100.00',
            'amount_residual': '$ 50.00',
            'amount_paid': '150.000 ☺',
            'currency': invoice.currency_id,
        }]])
