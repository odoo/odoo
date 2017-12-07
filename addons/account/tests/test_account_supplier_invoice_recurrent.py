# -*- coding: utf-8 -*-
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo.addons.account.tests.account_test_classes import AccountingTestCase


class TestAccountRecurrent(AccountingTestCase):

    def apply_vendor_cron(self):
        self.env.ref('account.recurrent_vendor_bills_cron').method_direct_trigger()

    def test_create_recurring_vendor_bills(self):
        AccountInvoice = self.env['account.invoice']
        invoice_account_id = self.env['account.account'].search([('user_type_id', '=', self.ref('account.data_account_type_receivable'))], limit=1).id
        invoice_line_account_id = self.env['account.account'].search([('user_type_id', '=', self.ref('account.data_account_type_expenses'))], limit=1).id
        purchase_journal = self.env['account.journal'].search([('type', '=', 'purchase')], limit=1)

        invoice_line_data = [
            (0, 0,
                {
                    'product_id': self.ref('product.product_product_4'),
                    'name': 'product 4 that cost 100',
                    'quantity': 1.0,
                    'price_unit': 100.0,
                    'account_id': invoice_line_account_id,
                    'name': 'product test 4',
                }
             ),
            (0, 0,
                {
                    'product_id': self.ref('product.product_product_5'),
                    'name': 'product 5 that cost 200',
                    'quantity': 2.0,
                    'price_unit': 200.0,
                    'account_id': invoice_line_account_id,
                    'name': 'product test 5',
                }
             )
        ]

        # Create an invoice dated 2 months before today
        invoice = AccountInvoice.create({
            'partner_id': self.ref('base.res_partner_2'),
            'account_id': invoice_account_id,
            'name': 'invoice test recurrent',
            'type': 'in_invoice',
            'reference_type': 'none',
            'date_invoice': datetime.today() + relativedelta(months=-2),
            'journal_id': purchase_journal.id,
            'is_recurrency_enabled': True,
            'recurrency_interval': 1,
            'recurrency_type': 'months',
            'invoice_line_ids': invoice_line_data
        })

        self.apply_vendor_cron()
        recurring_domain = [('type', '=', 'in_invoice'), ('state', '=', 'draft'), ('is_recurring_document', '=', True)]
        recurring_invoice_count = AccountInvoice.search_count(recurring_domain)
        # after executing crons for recurrent invoices verify that no invoices is auto generated if the recurrent invoice is in `draft` state
        self.assertEquals(recurring_invoice_count, 0, 'Recurring invoices should not be generated when invoice is in `draft` state.')

        invoice.action_invoice_open()  # Validate invoice
        self.apply_vendor_cron()
        # After validating invoice ran cron and then checked, 2 recurring invoices should be generated
        recurring_invoice_count = previous_recurring_invoice_count = AccountInvoice.search_count(recurring_domain)
        self.assertEquals(recurring_invoice_count, 2, '2 recurring invoices should be generated.')

        purchase_journal.write({'update_posted': True})  # Allow to cancel the invoice
        invoice.action_invoice_cancel()  # Cancel the invoice
        self.apply_vendor_cron()
        # verify that invoices isn't generated if invoice is in `cancel` state
        recurring_invoice_count = AccountInvoice.search_count(recurring_domain)
        self.assertEquals(previous_recurring_invoice_count, recurring_invoice_count, 'Recurring invoices should not be generated when invoice is in `cancel` state.')

        inv2_data = {
            'name': 'invoice test recurrent 2',
            'date_invoice': datetime.today() + relativedelta(months=-2),
            'is_recurrency_enabled': True,
            'recurrency_interval': 1,
            'recurrency_type': 'months',
        }

        invoice2 = invoice.copy(default=inv2_data)

        invoice2.action_invoice_open()  # Validate invoice
        Payment = self.env['account.payment']
        payment_vals = Payment.with_context(default_invoice_ids=[(4, invoice2.id, None)]).default_get(Payment._fields.keys())
        payment_vals.update({
            'payment_method_id': self.ref("account.account_payment_method_manual_out"),
            'journal_id': self.env['account.journal'].search([('type', '=', 'bank')], limit=1).id
        })
        # Register payment
        Payment.create(payment_vals).action_validate_invoice_payment()
        # verify that vendor bills are generated even when invoice is in `paid` state
        self.apply_vendor_cron()
        recurring_invoice_count = AccountInvoice.search_count(recurring_domain)
        self.assertEquals(recurring_invoice_count, previous_recurring_invoice_count + 2, '4 recurring invoices should be generated.')
