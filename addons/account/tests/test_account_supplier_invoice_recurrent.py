# -*- coding: utf-8 -*-
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo.addons.account.tests.account_test_classes import AccountingTestCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
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
                }
             ),
            (0, 0,
                {
                    'product_id': self.ref('product.product_product_5'),
                    'name': 'product 5 that cost 200',
                    'quantity': 2.0,
                    'price_unit': 200.0,
                    'account_id': invoice_line_account_id,
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
        recurring_domain = [('type', '=', 'in_invoice'), ('state', '=', 'draft'), ('is_recurring_document', '=', True)]

        # After executing cron, verify that no bill is auto generated if the recurrent bill is in `draft` state
        self.apply_vendor_cron()
        recurring_invoice_count = AccountInvoice.search_count(recurring_domain)
        self.assertEquals(recurring_invoice_count, 0, 'Recurring bills should not be generated when reference bill is still `draft`.')

        # After validating bill, run cron and check that 2 recurring bill have been generated
        invoice.action_invoice_open()  # Validate invoice
        self.apply_vendor_cron()
        recurring_invoice_count = previous_recurring_invoice_count = AccountInvoice.search_count(recurring_domain)
        self.assertEquals(recurring_invoice_count, 2, '2 recurring bills should be generated.')

        # verify that bills aren't generated if reference bill is in `cancel` state
        purchase_journal.write({'update_posted': True})  # Allow to cancel the invoice
        inv2_data = {
            'name': 'invoice test recurrent 2',
            'date_invoice': datetime.today() + relativedelta(months=-2),
            'is_recurrency_enabled': True,
            'recurrency_interval': 1,
            'recurrency_type': 'months',
        }
        invoice2 = invoice.copy(default=inv2_data)
        invoice2.action_invoice_cancel()  # Cancel the invoice
        self.apply_vendor_cron()
        recurring_invoice_count = AccountInvoice.search_count(recurring_domain)
        self.assertEquals(previous_recurring_invoice_count, recurring_invoice_count, 'Recurring bills should not be generated when reference bill is in `cancel` state.')

        # verify that vendor bills are generated even when invoice is in `paid` state
        inv3_data = {
            'name': 'invoice test recurrent 3',
            'date_invoice': datetime.today() + relativedelta(months=-2),
            'is_recurrency_enabled': True,
            'recurrency_interval': 1,
            'recurrency_type': 'months',
        }

        invoice3 = invoice.copy(default=inv3_data)
        invoice3.action_invoice_open()  # Validate invoice
        Payment = self.env['account.payment']
        payment_vals = Payment.with_context(default_invoice_ids=[(4, invoice3.id, None)]).default_get(Payment._fields.keys())
        payment_vals.update({
            'payment_method_id': self.ref("account.account_payment_method_manual_out"),
            'journal_id': self.env['account.journal'].search([('type', '=', 'bank')], limit=1).id
        })
        Payment.create(payment_vals).action_validate_invoice_payment()  # Register the payment
        self.apply_vendor_cron()
        recurring_invoice_count = AccountInvoice.search_count(recurring_domain)
        self.assertEquals(recurring_invoice_count, 4, '4 recurring bills should be generated.')
