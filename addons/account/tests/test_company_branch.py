# -*- coding: utf-8 -*-

from contextlib import nullcontext, closing
from freezegun import freeze_time
from functools import partial

from odoo import Command, fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged, Form


@tagged('post_install', '-at_install')
class TestCompanyBranch(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.other_currency = cls.setup_other_currency('EUR')

        cls.company_data['company'].write({
            'child_ids': [
                Command.create({'name': 'Branch A'}),
                Command.create({'name': 'Branch B'}),
            ],
        })
        cls.cr.precommit.run()  # load the CoA

        cls.root_company = cls.company_data['company']
        cls.branch_a, cls.branch_b = cls.root_company.child_ids

    def test_chart_template_loading(self):
        # Some company params have to be the same
        self.assertEqual(self.root_company.currency_id, self.branch_a.currency_id)
        self.assertEqual(self.root_company.fiscalyear_last_day, self.branch_a.fiscalyear_last_day)
        self.assertEqual(self.root_company.fiscalyear_last_month, self.branch_a.fiscalyear_last_month)

        # The accounts are shared
        root_accounts = self.env['account.account'].search([('company_ids', 'parent_of', self.root_company.id)])
        branch_a_accounts = self.env['account.account'].search([('company_ids', 'parent_of', self.branch_a.id)])
        self.assertTrue(root_accounts)
        self.assertEqual(root_accounts, branch_a_accounts)

        # The journals are shared
        root_journals = self.env['account.journal'].search([('company_id', 'parent_of', self.root_company.id)])
        branch_a_journals = self.env['account.journal'].search([('company_id', 'parent_of', self.branch_a.id)])
        self.assertTrue(root_journals)
        self.assertEqual(root_journals, branch_a_journals)

    def test_reconciliation(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2016-01-01',
            'company_id': self.branch_a.id,
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'product',
                    'price_unit': 1000,
                })
            ],
        })
        invoice.action_post()
        refund = self.env['account.move'].create({
            'move_type': 'out_refund',
            'invoice_date': '2017-01-01',
            'company_id': self.root_company.id,
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'product',
                    'price_unit': 1000,
                })
            ],
        })
        refund.action_post()

        payment_lines = (invoice + refund).line_ids.filtered(lambda l: l.display_type == 'payment_term')
        payment_lines.reconcile()
        self.assertEqual(payment_lines.mapped('amount_residual'), [0, 0])
        self.assertFalse(payment_lines.matched_debit_ids.exchange_move_id)

        # Can still open the invoice with only it's branch accessible
        self.env.invalidate_all()
        with Form(invoice.with_context(allowed_company_ids=self.branch_a.ids)):
            pass

    def test_reconciliation_foreign_currency(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2016-01-01',
            'company_id': self.branch_a.id,
            'currency_id': self.other_currency.id,
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'product',
                    'price_unit': 1000,
                })
            ],
        })
        invoice.action_post()
        refund = self.env['account.move'].create({
            'move_type': 'out_refund',
            'invoice_date': '2017-01-01',
            'company_id': self.root_company.id,
            'currency_id': self.other_currency.id,
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'product',
                    'price_unit': 1000,
                })
            ],
        })
        refund.action_post()

        payment_lines = (invoice + refund).line_ids.filtered(lambda l: l.display_type == 'payment_term')
        payment_lines.reconcile()
        self.assertEqual(payment_lines.mapped('amount_residual'), [0, 0])
        self.assertTrue(payment_lines.matched_debit_ids.exchange_move_id)
        self.assertTrue(payment_lines.matched_debit_ids.exchange_move_id.journal_id.company_id, invoice.company_id)

        # Can still open the invoice with only it's branch accessible
        self.env.invalidate_all()
        with Form(invoice.with_context(allowed_company_ids=self.branch_a.ids)):
            pass

    def test_lock_dates(self):
        moves = self.env['account.move'].search([])
        moves.filtered(lambda x: x.state != 'draft').button_draft()
        moves.unlink()
        for lock, lock_sale, lock_purchase in [
            ('hard_lock_date', True, True),
            ('fiscalyear_lock_date', True, True),
            ('tax_lock_date', True, True),
            ('sale_lock_date', True, False),
            ('purchase_lock_date', False, True),
        ]:
            for root_lock, branch_lock, invoice_date, company, move_type, failure_expected in (
                # before both locks
                ('3021-01-01', '3022-01-01', '3020-01-01', self.root_company, 'in_invoice', lock_purchase),
                ('3021-01-01', '3022-01-01', '3020-01-01', self.root_company, 'out_invoice', lock_sale),
                ('3021-01-01', '3022-01-01', '3020-01-01', self.branch_a, 'in_invoice', lock_purchase),
                ('3021-01-01', '3022-01-01', '3020-01-01', self.branch_a, 'out_invoice', lock_sale),
                # between root and branch lock
                ('3020-01-01', '3022-01-01', '3021-01-01', self.root_company, 'in_invoice', False),
                ('3020-01-01', '3022-01-01', '3021-01-01', self.root_company, 'out_invoice', False),
                ('3020-01-01', '3022-01-01', '3021-01-01', self.branch_a, 'in_invoice', lock_purchase),
                ('3020-01-01', '3022-01-01', '3021-01-01', self.branch_a, 'out_invoice', lock_sale),
                # between branch and root lock
                ('3022-01-01', '3020-01-01', '3021-01-01', self.root_company, 'in_invoice', lock_purchase),
                ('3022-01-01', '3020-01-01', '3021-01-01', self.root_company, 'out_invoice', lock_sale),
                ('3022-01-01', '3020-01-01', '3021-01-01', self.branch_a, 'in_invoice', lock_purchase),
                ('3022-01-01', '3020-01-01', '3021-01-01', self.branch_a, 'out_invoice', lock_sale),
                # after both locks
                ('3020-01-01', '3021-01-01', '3022-01-01', self.root_company, 'in_invoice', False),
                ('3020-01-01', '3021-01-01', '3022-01-01', self.root_company, 'out_invoice', False),
                ('3020-01-01', '3021-01-01', '3022-01-01', self.branch_a, 'in_invoice', False),
                ('3020-01-01', '3021-01-01', '3022-01-01', self.branch_a, 'out_invoice', False),
               ):
                with self.subTest(
                    lock=lock,
                    root_lock=root_lock,
                    branch_lock=branch_lock,
                    invoice_date=invoice_date,
                    move_type=move_type,
                    company=company.name,
                ), closing(self.env.cr.savepoint()):
                    check = partial(self.assertRaises, UserError) if failure_expected else nullcontext
                    move = self.init_invoice(
                        move_type, amounts=[100], taxes=self.root_company.account_sale_tax_id,
                        invoice_date=invoice_date, post=True, company=company,
                    )
                    self.assertEqual(move.date, fields.Date.to_date(invoice_date))
                    with freeze_time('4000-01-01'):  # ensure we don't lock in the future
                        self.root_company[lock] = root_lock
                        self.branch_a[lock] = branch_lock
                    with check():
                        move.button_draft()

    def test_change_record_company(self):
        account = self.env['account.account'].create({
            'name': 'volatile',
            'code': 'vola',
            'account_type': 'income',
            'company_ids': [Command.link(self.branch_a.id)]
        })
        account_lines = [Command.create({
            'account_id': account.id,
            'name': 'name',
        })]
        tax = self.env['account.tax'].create({
            'name': 'volatile',
        })
        tax_lines = [Command.create({
            'account_id': self.root_company.account_journal_suspense_account_id.id,
            'tax_ids': [Command.set(tax.ids)],
            'name': 'name',
        })]
        for record, lines, company_field in (
            (account, account_lines, 'company_ids'),
            (tax, tax_lines, 'company_id'),
        ):
            with self.subTest(model=record._name):
                self.env['account.move'].create({'company_id': self.branch_a.id, 'line_ids': lines})
                # Can switch to main
                record[company_field] = self.root_company

                # Can switch back
                record[company_field] = self.branch_a

                # Can't use in main if owned by a branch
                with self.assertRaisesRegex(UserError, 'belongs to another company'):
                    self.env['account.move'].create({'company_id': self.root_company.id, 'line_ids': lines})

                # Can still switch to main
                record[company_field] = self.root_company

                # Can use in main now
                self.env['account.move'].create({'company_id': self.root_company.id, 'line_ids': lines})

                # Can't switch back to branch if used in main
                with self.assertRaisesRegex(UserError, 'journal items linked'):
                    record[company_field] = self.branch_a

    def test_branch_should_keep_parent_company_currency(self):
        test_country = self.env['res.country'].create({
            'name': 'Gold Country',
            'code': 'zz',
            'currency_id': self.other_currency.id
        })
        root_company = self.env['res.company'].create({
            'name': 'Gold Company',
            'country_id': test_country.id,
        })
        # with the generic_coa, try_loading forces currency_id to USD and account_fiscal_country_id to United States
        self.env['account.chart.template'].try_loading('generic_coa', company=root_company, install_demo=False)
        # So we write these values after try_loading
        root_company.write({
            'currency_id': test_country.currency_id.id,
            'account_fiscal_country_id': test_country.id,
        })

        root_company.write({
            'child_ids': [
                Command.create({
                    'name': 'Gold Branch',
                    'country_id': test_country.id,
                }),
            ],
        })
        self.env['account.chart.template'].try_loading('generic_coa', company=root_company.child_ids[0], install_demo=False)
        self.assertEqual(root_company.currency_id, root_company.child_ids[0].currency_id)

    def test_switch_company_currency(self):
        """
        A user should not be able to switch the currency of another company
        when that company already has posted account move lines.
        """
        # Create company A (user's company)
        company_a = self.env['res.company'].create({
            'name': "Company A",
        })

        # Get company B from test setup
        company_b = self.company_data['company']

        # Create a purchase journal for company B
        journal = self.env['account.journal'].create({
            'name': "Vendor Bills Journal",
            'code': "VEND",
            'type': "purchase",
            'company_id': company_b.id,
            'currency_id': company_b.currency_id.id,
        })

        # Create an invoice for company B
        invoice = self.env['account.move'].create({
            'move_type': "in_invoice",
            'company_id': company_b.id,
            'journal_id': journal.id,
        })
        invoice.currency_id = self.env.ref('base.USD').id

        # Add a line to the invoice using an expense account
        self.env['account.move.line'].create({
            'move_id': invoice.id,
            'account_id': self.company_data["default_account_expense"].id,
            'name': "Test Invoice Line",
            'company_id': company_b.id,
        })

        # Create a user that only belongs to company A
        user = self.env['res.users'].create({
            'name': "User A",
            'login': "user_a@example.com",
            'email': "user_a@example.com",
            'company_id': company_a.id,
            'company_ids': [Command.set([company_a.id])],
        })

        # Try to change company B's currency as user A (should raise UserError)
        user_env = self.env(user=user)
        with self.assertRaises(UserError):
            user_env['res.company'].browse(company_b.id).write({
                'currency_id': self.env.ref('base.EUR').id,
            })

    def test_set_fiscalyear_last_day_to_negative_value(self):
        """Test that ensure that fiscalyear_last_day raises ValidationError when set
           to negative value."""
        with self.assertRaises(ValidationError):
            self.root_company.fiscalyear_last_day = -1
