# Make sure / performs a floating point division even if environment is python 2
from __future__ import division

from odoo.addons.account.tests.account_test_classes import AccountingTestCase
from odoo.addons.l10n_us_check_printing.report import print_check
from odoo.tests import tagged
import time

import math


@tagged('post_install', '-at_install')
class TestPrintCheck(AccountingTestCase):

    def setUp(self):
        super(TestPrintCheck, self).setUp()

        self.invoice_model = self.env['account.invoice']
        self.invoice_line_model = self.env['account.invoice.line']
        self.register_payments_model = self.env['account.register.payments']

        self.partner_axelor = self.env.ref("base.res_partner_2")
        self.product = self.env.ref("product.product_product_4")
        self.payment_method_check = self.env.ref("account_check_printing.account_payment_method_check")

        self.account_payable = self.env['account.account'].search([('user_type_id', '=', self.env.ref('account.data_account_type_payable').id)], limit=1)
        self.account_expenses = self.env['account.account'].search([('user_type_id', '=', self.env.ref('account.data_account_type_expenses').id)], limit=1)

        self.bank_journal = self.env['account.journal'].create({'name': 'Bank', 'type': 'bank', 'code': 'BNK67'})
        self.bank_journal.check_manual_sequencing = True

    def create_invoice(self, amount=100, is_refund=False):
        invoice = self.invoice_model.create({
            'partner_id': self.partner_axelor.id,
            'name': is_refund and "Supplier Refund" or "Supplier Invoice",
            'type': is_refund and "in_refund" or "in_invoice",
            'account_id': self.account_payable.id,
            'date_invoice': time.strftime('%Y') + '-06-26',
        })
        self.invoice_line_model.create({
            'product_id': self.product.id,
            'quantity': 1,
            'price_unit': is_refund and amount / 4 or amount,
            'invoice_id': invoice.id,
            'name': 'something',
            'account_id': self.account_expenses.id,
        })
        invoice.action_invoice_open()
        return invoice

    def create_payment(self, invoices):
        register_payments = self.register_payments_model.with_context({
            'active_model': 'account.invoice',
            'active_ids': invoices.ids
        }).create({
            'payment_date': time.strftime('%Y') + '-07-15',
            'journal_id': self.bank_journal.id,
            'payment_method_id': self.payment_method_check.id,
        })
        register_payments.create_payments()
        return self.env['account.payment'].search([], order="id desc", limit=1)

    def test_print_check(self):
        # Make a payment for 10 invoices and 5 credit notes
        invoices = self.env['account.invoice']
        for i in range(0,15):
            invoices |= self.create_invoice(is_refund=(i % 3 == 0))
        payment = self.create_payment(invoices)

        # Check the data generated for the report
        self.env.ref('base.main_company').write({'account_check_printing_multi_stub': True})
        report_pages = payment._check_get_pages()
        self.assertEqual(len(report_pages), int(math.ceil(len(invoices.ids) / print_check.INV_LINES_PER_STUB)))
        self.env.ref('base.main_company').write({'account_check_printing_multi_stub': False})
        report_pages = payment._check_get_pages()
        self.assertEqual(len(report_pages), 1)
