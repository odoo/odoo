# -*- coding: utf-8 -*-

import datetime
from freezegun import freeze_time

from odoo.addons.account.tests.account_test_savepoint import AccountTestInvoicingCommon
from odoo.addons.payment.controllers.portal import PaymentProcessing
from odoo.addons.website.tools import MockRequest
from odoo.tests.common import tagged

@tagged('post_install', '-at_install')
class TestInvoices(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super(TestInvoices, cls).setUpClass()

        cls.bank_journal = cls.company_data['default_journal_bank']
        cls.bank_journal.default_credit_account_id = cls.bank_journal.default_debit_account_id.copy()

        cls.company_id = cls.company_data['company'].id

        cls.payment_test = cls.env.ref('payment_test.payment_acquirer_test')
        cls.payment_test.company_id = cls.company_id

        cls.partner_a.country_id = cls.env['res.country'].search([('code', 'like', 'US')], limit=1)

        public_user = cls.env.ref('base.public_user')
        cls.website = cls.env['website'].browse(1).with_user(public_user)
        cls.WebsiteController = PaymentProcessing()

    def _create_transaction(self):
        payment = self.env['account.payment'].create({
            'journal_id': self.bank_journal.id,
            'amount': 1500,
            'payment_type': 'inbound',
            'partner_id' : self.partner_a.id,
            'partner_type': 'customer',
            'payment_method_id': self.env.ref('payment.account_payment_method_electronic_in').id,
        })

        tx = self.env['payment.transaction'].sudo().create({
            'reference': str(payment.id),
            'currency_id': self.currency_data['currency'].id,
            'acquirer_id': self.payment_test.id,
            'partner_id': self.partner_a.id,
            'payment_id': payment.id,
            'amount': 1500.0,
        })
        tx.invoice_ids = [(0, 0, {
            'type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'company_id': self.company_id,
            'currency_id': self.currency_data['currency'].id,
            'invoice_line_ids': [(0, None, {
                    'product_id': self.product_a.id,
                    'quantity': 3,
                    'price_unit': 500,
                })]
        })]

        return tx

    @freeze_time("2021-06-19 01:33:00") # UTC
    def test_invoice_date(self):
        """Test posted invoice date when customer isn't logged in"""

        self.company_data['company'].partner_id.tz = 'America/Los_Angeles'
        tx = self._create_transaction()

        with MockRequest(self.website.env, website=self.website):
            self.WebsiteController.add_payment_transaction(tx)
            self.WebsiteController.payment_status_poll()

        self.assertEqual(tx.invoice_ids.date, datetime.date(2021, 6, 18), 'Payment: Wrong Invoice date - Customer not logged in')
