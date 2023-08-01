# -*- coding: utf-8 -*-

from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.exceptions import UserError, ValidationError


@tagged('post_install', '-at_install')
class TestAccountTax(AccountTestInvoicingCommon):

    def test_changing_tax_company(self):
        ''' Ensure you can't change the company of an account.tax if there are some journal entries '''

        # Avoid duplicate key value violates unique constraint "account_tax_name_company_uniq".
        self.company_data['default_tax_sale'].name = 'test_changing_account_company'

        self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2019-01-01',
            'invoice_line_ids': [
                (0, 0, {
                    'name': 'invoice_line',
                    'quantity': 1.0,
                    'price_unit': 100.0,
                    'tax_ids': [(6, 0, self.company_data['default_tax_sale'].ids)],
                }),
            ],
        })

        with self.assertRaises(UserError), self.cr.savepoint():
            self.company_data['default_tax_sale'].company_id = self.company_data_2['company']

    def test_tax_is_used_when_in_transactions(self):
        ''' Ensures that a tax is set to used when it is part of some transactions '''

        # Account.move is one type of transaction
        tax_invoice = self.env['account.tax'].create({
            'name': 'test_is_used_invoice',
            'amount': '100',
        })

        self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2023-01-01',
            'invoice_line_ids': [
                Command.create({
                    'name': 'invoice_line',
                    'quantity': 1.0,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(tax_invoice.ids)],
                }),
            ],
        })
        tax_invoice.invalidate_model(fnames=['is_used'])
        self.assertTrue(tax_invoice.is_used)

        # Account.reconcile is another of transaction
        tax_reconciliation = self.env['account.tax'].create({
            'name': 'test_is_used_reconcilition',
            'amount': '100',
        })
        self.env['account.reconcile.model'].create({
            'name': "test_tax_is_used",
            'rule_type': 'writeoff_suggestion',
            'auto_reconcile': False,
            'line_ids': [Command.create({
                'account_id': self.company_data['default_account_revenue'].id,
                'tax_ids': [Command.set(tax_reconciliation.ids)],
            })],
        })
        tax_reconciliation.invalidate_model(fnames=['is_used'])
        self.assertTrue(tax_reconciliation.is_used)

    def test_tax_is_used_restrictions(self):
        ''' You should not be able to modify some values of a used tax '''

        tax = self.env['account.tax'].create({
            'name': 'test_is_used',
            'amount': '100',
        })

        # A newly created tax should not be used
        self.assertFalse(tax.is_used)

        self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2023-01-01',
            'invoice_line_ids': [
                Command.create({
                    'name': 'invoice_line',
                    'quantity': 1.0,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(tax.ids)],
                }),
            ],
        })
        tax.invalidate_model(fnames=['is_used'])

        #   amount_type
        with self.assertRaises(ValidationError), self.cr.savepoint():
            tax.amount_type = 'fixed'

        #   type_tax_use
        with self.assertRaises(ValidationError), self.cr.savepoint():
            tax.type_tax_use = 'purchase'

        #   price_include
        with self.assertRaises(ValidationError), self.cr.savepoint():
            tax.price_include = True

        #   include_base_amount
        with self.assertRaises(ValidationError), self.cr.savepoint():
            tax.include_base_amount = True

        #   add repartition lines
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.env['account.tax.repartition.line'].create([
                {'tax_id': tax.id, 'document_type': 'invoice', 'repartition_type': 'tax', 'factor': -100},
                {'tax_id': tax.id, 'document_type': 'refund', 'repartition_type': 'tax', 'factor': -100},
            ])

        #   remove repartition lines
        with self.assertRaises(ValidationError), self.cr.savepoint():
            invoice_repartition_lines = tax.invoice_repartition_line_ids
            for rep_line in invoice_repartition_lines:
                rep_line.unlink()
