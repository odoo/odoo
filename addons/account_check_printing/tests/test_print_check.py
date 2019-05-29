# Make sure / performs a floating point division even if environment is python 2
from __future__ import division

from odoo.addons.account.tests.account_test_classes import AccountingTestCase
from odoo.addons.account_check_printing.models.account_payment import INV_LINES_PER_STUB
from odoo.tests import tagged
from odoo.tests.common import Form
import time
import math



@tagged('post_install', '-at_install')
class TestPrintCheck(AccountingTestCase):

    def setUp(self):
        super(TestPrintCheck, self).setUp()

        self.invoice_model = self.env['account.move']
        self.invoice_line_model = self.env['account.move.line']
        self.payment_model = self.env['account.payment']

        self.partner_axelor = self.env.ref("base.res_partner_2")
        self.product = self.env.ref("product.product_product_4")
        self.payment_method_check = self.env.ref("account_check_printing.account_payment_method_check")

        self.account_payable = self.env['account.account'].search([('user_type_id', '=', self.env.ref('account.data_account_type_payable').id)], limit=1)
        self.account_expenses = self.env['account.account'].search([('user_type_id', '=', self.env.ref('account.data_account_type_expenses').id)], limit=1)

        self.bank_journal = self.env['account.journal'].create({'name': 'Bank', 'type': 'bank', 'code': 'BNK67'})
        self.bank_journal.check_manual_sequencing = True

    def create_invoice(self, amount=100, is_refund=False):
        invoice = self.env['account.move'].with_context(default_type=is_refund and 'out_refund' or 'in_invoice').create({
            'partner_id': self.partner_axelor.id,
            'invoice_date': time.strftime('%Y') + '-06-26',
            'date': time.strftime('%Y') + '-06-26',
            'invoice_line_ids': [
                (0, 0, {
                    'product_id': self.product.id,
                    'quantity': 1,
                    'price_unit': is_refund and amount / 4 or amount,
                })
            ]
        })
        invoice.post()
        return invoice

    def create_payment(self, invoices):
        payment_register = Form(self.env['account.payment'].with_context(active_model='account.move', active_ids=invoices.ids))
        payment_register.payment_date = time.strftime('%Y') + '-07-15'
        payment_register.journal_id = self.bank_journal
        payment_register.payment_method_id = self.payment_method_check
        payment = payment_register.save()
        payment.post()
        return payment

    def test_print_check(self):
        # Make a payment for 10 invoices and 5 credit notes
        invoices = self.env['account.move']
        for i in range(0, 15):
            invoices |= self.create_invoice(is_refund=(i % 3 == 0))
        payment = self.create_payment(invoices)
        self.assertEqual(all(payment.mapped('check_amount_in_words')), True, 'The amount in words is not set on all the payments')
        self.assertEqual(all(payment.mapped('check_number')), True, 'The check number is not set on all the payments')

        # Check the data generated for the report
        self.env.ref('base.main_company').write({'account_check_printing_multi_stub': True})
        report_pages = payment._check_get_pages()
        self.assertEqual(len(report_pages), int(math.ceil(len(payment.reconciled_invoice_ids) / INV_LINES_PER_STUB)))
        self.env.ref('base.main_company').write({'account_check_printing_multi_stub': False})
        report_pages = payment._check_get_pages()
        self.assertEqual(len(report_pages), 1)

    def test_from_register(self):
        invoices = self.env['account.move']
        for i in range(0, 3):
            invoices |= self.create_invoice(is_refund=(i % 3 == 0))
        payment = self.create_payment(invoices)
        self.assertEqual(all(payment.mapped('check_amount_in_words')), True, 'The amount in words is not set on all the payments')
