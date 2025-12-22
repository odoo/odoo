# -*- coding: utf-8 -*-

from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.exceptions import UserError


@tagged('post_install', '-at_install')
class TestAccountTax(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data_2 = cls.setup_other_company()

    @classmethod
    def default_env_context(cls):
        # OVERRIDE
        return {}

    def set_up_and_use_tax(self):

        self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2023-01-01',
            'invoice_line_ids': [
                Command.create({
                    'name': 'invoice_line',
                    'quantity': 1.0,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(self.company_data['default_tax_sale'].ids)],
                }),
            ],
        })

        # Create two lines after creating the move so that those lines are not used in the move
        self.company_data['default_tax_sale'].write({
            'invoice_repartition_line_ids': [
                Command.create({'repartition_type': 'tax', 'factor_percent': 0.0}),
            ],
            'refund_repartition_line_ids': [
                Command.create({'repartition_type': 'tax', 'factor_percent': 0.0}),
            ],
        })

        self.flush_tracking()
        self.assertTrue(self.company_data['default_tax_sale'].is_used)

    def flush_tracking(self):
        """ Force the creation of tracking values. """
        self.env.flush_all()
        self.cr.flush()

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

    def test_logging_of_tax_update_when_tax_is_used(self):
        """ Modifications of a used tax should be logged. """

        self.set_up_and_use_tax()

        self.company_data['default_tax_sale'].write({
            'name': self.company_data['default_tax_sale'].name + ' MODIFIED',
            'amount': 21,
            'amount_type': 'fixed',
            'type_tax_use': 'purchase',
            'price_include_override': 'tax_included',
            'include_base_amount': True,
            'is_base_affected': False,
        })
        self.flush_tracking()
        self.assertEqual(len(self.company_data['default_tax_sale'].message_ids), 1,
                         "Only 1 message should have been created when updating all the values.")
        # There are 7 tracked values in account.tax and we update each of them, each on should be included in the message
        self.assertEqual(len(self.company_data['default_tax_sale'].message_ids.tracking_value_ids), 7,
                         "The number of updated value should be 7.")

    def test_logging_of_repartition_lines_addition_when_tax_is_used(self):
        """ Adding repartition lines in a used tax should be logged. """

        self.set_up_and_use_tax()

        self.company_data['default_tax_sale'].write({
            'invoice_repartition_line_ids': [
                Command.create({'repartition_type': 'tax', 'factor_percent': -100.0}),
            ],
            'refund_repartition_line_ids': [
                Command.create({'repartition_type': 'tax', 'factor_percent': -100.0}),
            ],
        })
        self.flush_tracking()

        previews = self.company_data['default_tax_sale'].message_ids.mapped('preview')
        self.assertIn(
            "New Invoice repartition line 4: -100.0 (Factor Percent) None (Account) None (Tax Grids) False (Use in tax closing)",
            previews
        )
        self.assertIn(
            "New Refund repartition line 4: -100.0 (Factor Percent) None (Account) None (Tax Grids) False (Use in tax closing)",
            previews
        )

    def test_logging_of_repartition_lines_update_when_tax_is_used(self):
        """ Updating repartition lines in a used tax should be logged. """

        self.set_up_and_use_tax()

        last_invoice_rep_line = self.company_data['default_tax_sale'].invoice_repartition_line_ids\
            .filtered(lambda tax_rep: not tax_rep.factor_percent)
        last_refund_rep_line = self.company_data['default_tax_sale'].refund_repartition_line_ids\
            .filtered(lambda tax_rep: not tax_rep.factor_percent)

        self.company_data['default_tax_sale'].write({
            "invoice_repartition_line_ids": [
                Command.update(last_invoice_rep_line.id, {
                    'factor_percent': -100,
                    'tag_ids': [Command.create({'name': 'TaxTag12345'})]
                }),
            ],
            "refund_repartition_line_ids": [
                Command.update(last_refund_rep_line.id, {
                    'factor_percent': -100,
                    'account_id': self.company_data['default_account_tax_purchase'].id,
                }),
            ],
        })
        self.flush_tracking()

        previews = self.company_data['default_tax_sale'].message_ids.mapped('preview')
        self.assertIn("Invoice repartition line 3: 0.0 -100.0 (Factor Percent) None ['TaxTag12345'] (Tax Grids)", previews)
        self.assertIn("Refund repartition line 3: 0.0 -100.0 (Factor Percent) None 131000 Tax Paid (Account) False True (Use in tax closing)", previews)

    def test_logging_of_repartition_lines_reordering_when_tax_is_used(self):
        """ Reordering repartition lines in a used tax should be logged. """

        self.set_up_and_use_tax()

        last_invoice_rep_line = self.company_data['default_tax_sale'].invoice_repartition_line_ids\
            .filtered(lambda tax_rep: not tax_rep.factor_percent)
        last_refund_rep_line = self.company_data['default_tax_sale'].refund_repartition_line_ids\
            .filtered(lambda tax_rep: not tax_rep.factor_percent)

        self.company_data['default_tax_sale'].write({
            "invoice_repartition_line_ids": [
                Command.update(last_invoice_rep_line.id, {'sequence': 0}),
            ],
            "refund_repartition_line_ids": [
                Command.update(last_refund_rep_line.id, {'sequence': 0}),
            ],
        })
        self.flush_tracking()

        previews = self.company_data['default_tax_sale'].message_ids.mapped('preview')
        self.assertIn("Invoice repartition line 1: 100.0 0.0 (Factor Percent)", previews)
        self.assertIn("Invoice repartition line 3: 0.0 100.0 (Factor Percent) None 251000 Tax Received (Account) False True (Use in tax closing)", previews)

    def test_logging_of_repartition_lines_removal_when_tax_is_used(self):
        """ Deleting repartition lines in a used tax should be logged. """

        self.set_up_and_use_tax()

        last_invoice_rep_line = self.company_data['default_tax_sale'].invoice_repartition_line_ids.sorted(key=lambda r: r.sequence)[-1]
        last_refund_rep_line = self.company_data['default_tax_sale'].refund_repartition_line_ids.sorted(key=lambda r: r.sequence)[-1]

        self.company_data['default_tax_sale'].write({
            "invoice_repartition_line_ids": [
                Command.delete(last_invoice_rep_line.id),
            ],
            "refund_repartition_line_ids": [
                Command.delete(last_refund_rep_line.id),
            ],
        })
        self.flush_tracking()

        previews = self.company_data['default_tax_sale'].message_ids.mapped('preview')
        self.assertIn(
            "Removed Invoice repartition line 3: 0.0 (Factor Percent) None (Account) None (Tax Grids) False (Use in tax closing)",
            previews
        )
        self.assertIn(
            "Removed Refund repartition line 3: 0.0 (Factor Percent) None (Account) None (Tax Grids) False (Use in tax closing)",
            previews
        )

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

    def test_tax_no_duplicate_in_repartition_line(self):
        """ Test that whenever a tax generate a second tax line
            the same tax is not applied to the tax line.
        """

        account_1 = self.company_data['default_account_tax_sale'].copy()
        account_2 = self.company_data['default_account_tax_sale'].copy()
        tax = self.env['account.tax'].create({
            'name': "tax",
            'amount': 15.0,
            'include_base_amount': True,
            'invoice_repartition_line_ids': [
                Command.create({
                    'repartition_type': 'base',
                }),
                Command.create({
                    'factor_percent': 100,
                    'repartition_type': 'tax',
                    'account_id': account_1.id,
                }),
                Command.create({
                    'factor_percent': -100,
                    'repartition_type': 'tax',
                    'account_id': account_2.id,
                }),
            ],
            'refund_repartition_line_ids': [
                Command.create({
                    'repartition_type': 'base',
                }),
                Command.create({
                    'factor_percent': 100,
                    'repartition_type': 'tax',
                    'account_id': account_1.id,
                }),
                Command.create({
                    'factor_percent': -100,
                    'repartition_type': 'tax',
                    'account_id': account_2.id,
                }),
            ],
        })

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2019-01-01',
            'invoice_line_ids': [
                Command.create({
                    'name': 'invoice_line',
                    'quantity': 1.0,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(tax.ids)],
                }),
            ],
        })

        self.assertRecordValues(invoice, [{
            'amount_untaxed': 100.0,
            'amount_tax': 0.0,
            'amount_total': 100.0,
        }])
        self.assertRecordValues(invoice.line_ids, [
            {'display_type': 'product',         'tax_ids': tax.ids,     'balance': -100.0,  'account_id': self.company_data['default_account_revenue'].id},
            {'display_type': 'tax',             'tax_ids': [],          'balance': -15.0,   'account_id': account_1.id},
            {'display_type': 'tax',             'tax_ids': [],          'balance': 15.0,    'account_id': account_2.id},
            {'display_type': 'payment_term',    'tax_ids': [],          'balance': 100.0,   'account_id': self.company_data['default_account_receivable'].id},
        ])
