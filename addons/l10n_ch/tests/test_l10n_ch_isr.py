# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from odoo.addons.account.tests.account_test_classes import AccountingTestCase
from odoo.exceptions import ValidationError
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class ISRTest(AccountingTestCase):

    def create_invoice(self, currency_to_use='base.CHF'):
        """ Generates a test invoice """
        account_receivable = self.env['account.account'].search([('user_type_id', '=', self.env.ref('account.data_account_type_receivable').id)], limit=1)
        currency = self.env.ref(currency_to_use)
        partner_agrolait = self.env.ref("base.res_partner_2")
        product = self.env.ref("product.product_product_4")
        account_revenue = self.env['account.account'].search([('user_type_id', '=', self.env.ref('account.data_account_type_revenue').id)], limit=1)

        invoice = self.env['account.invoice'].create({
            'partner_id': partner_agrolait.id,
            'currency_id': currency.id,
            'name': 'invoice to client',
            'account_id': account_receivable.id,
            'type': 'out_invoice',
            'date_invoice': time.strftime('%Y') + '-12-22',
        })

        self.env['account.invoice.line'].create({
            'product_id': product.id,
            'quantity': 1,
            'price_unit': 42,
            'invoice_id': invoice.id,
            'name': 'something',
            'account_id': account_revenue.id,
        })

        invoice.action_invoice_open()

        return invoice

    def create_account(self, number):
        """ Generates a test res.partner.bank. """
        return self.env['res.partner.bank'].create({
            'acc_number': number
        })

    def print_isr(self, invoice):
        try:
            invoice.isr_print()
            return True
        except ValidationError:
            return False

    def isr_not_generated(self, invoice):
        """ Prints the given invoice and tests that no ISR generation is triggered. """
        self.assertFalse(self.print_isr(invoice), 'No ISR should be generated for this invoice')

    def isr_generated(self, invoice):
        """ Prints the given invoice and tests that an ISR generation is triggered. """
        self.assertTrue(self.print_isr(invoice), 'An ISR should have been generated')

    def test_l10n_ch_postals(self):
        #An account whose number is set to a valid postal number becomes a 'postal'
        #account and sets its postal reference field.
        account_test_postal_ok = self.create_account('010391391')
        self.assertEqual(account_test_postal_ok.acc_type, 'postal', "A valid postal number in acc_number should set its type to 'postal'")
        self.assertEqual(account_test_postal_ok.l10n_ch_postal, '010391391', "A postal account should have a postal reference identical to its account number")

        #An account whose number is set to a non-postal value should not get the
        #'postal' type
        account_test_postal_wrong = self.create_account('010391394')
        self.assertNotEqual(account_test_postal_wrong.acc_type, 'postal', "A non-postal account cannot be of type 'postal'")

        #A swiss IBAN account contains a postal reference
        account_test_iban_ok = self.create_account('CH6309000000250097798')
        self.assertEqual(account_test_iban_ok.acc_type, 'iban', "The IBAN must be valid")
        self.assertEqual(account_test_iban_ok.l10n_ch_postal, '000250097798', "A valid swiss IBAN should set the postal reference")

        #A non-swiss IBAN must not allow the computation of a postal reference
        account_test_iban_wrong = self.create_account('GR1601101250000000012300695')
        self.assertEqual(account_test_iban_wrong.acc_type, 'iban', "The IBAN must be valid")
        self.assertFalse(account_test_iban_wrong.l10n_ch_postal, "A valid swiss IBAN should set the postal reference")

    def test_isr(self):
        #Let us test the generation of an ISR for an invoice, first by showing an
        #ISR report is only generated when Odoo has all the data it needs.
        invoice_1 = self.create_invoice('base.CHF')
        self.isr_not_generated(invoice_1)

        #Now we add an account for payment to our invoice, but still cannot generate the ISR
        test_account = self.create_account('250097798')
        invoice_1.partner_bank_id = test_account
        self.isr_not_generated(invoice_1)

        #Finally, we add bank coordinates to our account. The ISR should now be available to generate
        test_bank = self.env['res.bank'].create({
                'name':'Money Drop',
                'l10n_ch_postal_chf':'010391391'
        })

        test_account.bank_id = test_bank
        self.isr_generated(invoice_1)

        #Now, let us show that, with the same data, an invoice in euros does not generate any ISR (because the bank does not have any EUR postal reference)
        invoice_2 = self.create_invoice('base.EUR')
        invoice_2.partner_bank_id = test_account
        self.isr_not_generated(invoice_2)
