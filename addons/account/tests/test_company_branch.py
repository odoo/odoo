# -*- coding: utf-8 -*-

from contextlib import nullcontext
from freezegun import freeze_time
from functools import partial

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import Form, tagged, users

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestCompanyBranch(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref)

        cls.company_data['company'].write({
            'child_ids': [
                Command.create({'name': 'Branch A'}),
                Command.create({'name': 'Branch B'}),
            ],
        })
        cls.cr.precommit.run()  # load the CoA

        cls.root_company = cls.company_data['company']
        cls.branch_a, cls.branch_b = cls.root_company.child_ids

        cls.branch_user = cls.env['res.users'].create({
            'name': 'Branch user',
            'login': 'branch_user',
            'company_id': cls.branch_a.id,
            'company_ids': [(6, 0, [cls.root_company.id,
                                    cls.branch_a.id])],
            'groups_id': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('account.group_account_invoice').id,
            ])],
        })

    def test_chart_template_loading(self):
        # Some company params have to be the same
        self.assertEqual(self.root_company.currency_id, self.branch_a.currency_id)
        self.assertEqual(self.root_company.fiscalyear_last_day, self.branch_a.fiscalyear_last_day)
        self.assertEqual(self.root_company.fiscalyear_last_month, self.branch_a.fiscalyear_last_month)

        # The accounts are shared
        root_accounts = self.env['account.account'].search([('company_id', 'parent_of', self.root_company.id)])
        branch_a_accounts = self.env['account.account'].search([('company_id', 'parent_of', self.branch_a.id)])
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
            'currency_id': self.currency_data['currency'].id,
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
            'currency_id': self.currency_data['currency'].id,
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
        for lock in ['fiscalyear_lock_date', 'tax_lock_date']:
            for root_lock, branch_lock, invoice_date, company, expected in (
                # before both locks
                ('3021-01-01', '3022-01-01', '3020-01-01', self.root_company, 'fail'),
                ('3021-01-01', '3022-01-01', '3020-01-01', self.branch_a, 'fail'),
                # between root and branch lock
                ('3020-01-01', '3022-01-01', '3021-01-01', self.root_company, 'success'),
                ('3020-01-01', '3022-01-01', '3021-01-01', self.branch_a, 'fail'),
                # between branch and root lock
                ('3022-01-01', '3020-01-01', '3021-01-01', self.root_company, 'fail'),
                ('3022-01-01', '3020-01-01', '3021-01-01', self.branch_a, 'fail'),
                # after both locks
                ('3020-01-01', '3021-01-01', '3022-01-01', self.root_company, 'success'),
                ('3020-01-01', '3021-01-01', '3022-01-01', self.branch_a, 'success'),
            ):
                with self.subTest(
                    lock=lock,
                    root_lock=root_lock,
                    branch_lock=branch_lock,
                    invoice_date=invoice_date,
                    company=company.name,
                ), self.env.cr.savepoint() as sp:
                    with freeze_time('4000-01-01'):  # ensure we don't lock in the future
                        self.root_company[lock] = root_lock
                        self.branch_a[lock] = branch_lock
                    check = partial(self.assertRaises, UserError) if expected == 'fail' else nullcontext
                    with check():
                        self.init_invoice(
                            'out_invoice', amounts=[100], taxes=self.root_company.account_sale_tax_id,
                            invoice_date=invoice_date, post=True, company=company,
                        )
                    sp.close()

    def test_change_record_company(self):
        account = self.env['account.account'].create({
            'name': 'volatile',
            'code': 'vola',
            'account_type': 'income',
            'company_id': self.branch_a.id,
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
        for record, lines in (
            (account, account_lines),
            (tax, tax_lines),
        ):
            with self.subTest(model=record._name):
                self.env['account.move'].create({'company_id': self.branch_a.id, 'line_ids': lines})
                # Can switch to main
                record.company_id = self.root_company

                # Can switch back
                record.company_id = self.branch_a

                # Can't use in main if owned by a branch
                with self.assertRaisesRegex(UserError, 'belongs to another company'):
                    self.env['account.move'].create({'company_id': self.root_company.id, 'line_ids': lines})

                # Can still switch to main
                record.company_id = self.root_company

                # Can use in main now
                self.env['account.move'].create({'company_id': self.root_company.id, 'line_ids': lines})

                # Can't switch back to branch if used in main
                with self.assertRaisesRegex(UserError, 'journal items linked'):
                    record.company_id = self.branch_a

    def test_branch_should_keep_parent_company_currency(self):
        test_country = self.env['res.country'].create({
            'name': 'Gold Country',
            'code': 'zz',
            'currency_id': self.currency_data['currency'].id
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
        company_b = self.company_data_2['company']

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
            'account_id': self.company_data_2["default_account_expense"].id,
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
            'groups_id': [Command.set([
                self.env.ref('base.group_system').id,
                self.env.ref('base.group_erp_manager').id,
                self.env.ref('account.group_account_user').id,
            ])],
        })

        # Try to change company B's currency as user A (should raise UserError)
        user_env = self.env(user=user)
        with self.assertRaises(UserError):
            user_env['res.company'].browse(company_b.id).write({
                'currency_id': self.env.ref('base.EUR').id,
            })

    @users('branch_user')
    def test_branch_user_can_assign_outstanding_credit_with_parent_access(self):
        """Branch user (Billing) who can *see* both companies but keeps only
        the branch active should still be able to reconcile an outstanding
        credit without hitting AccessError."""

        invoice = self.env['account.move'].with_context(allowed_company_ids=self.branch_a.ids).create({
            'move_type':  'out_invoice',
            'company_id': self.branch_a.id,
            'partner_id': self.partner_a.id,
            'invoice_date': '2025-01-01',
            'invoice_line_ids': [Command.create({
                'name': 'Consulting service',
                'price_unit': 100,
                'tax_ids': False,
            })],
        })
        invoice.action_post()

        payment = self.env['account.payment'].with_context(allowed_company_ids=self.branch_a.ids).create({
            'payment_type':   'inbound',
            'partner_type':   'customer',
            'partner_id':     self.partner_a.id,
            'amount':         invoice.amount_total,
            'journal_id':     self.company_data['default_journal_bank'].id,
            'payment_method_line_id': self.inbound_payment_method_line.id,
            'company_id':     self.branch_a.id,
        })
        payment.action_post()

        self.root_company.invalidate_recordset(['tax_exigibility'], flush=False)
        (invoice + payment.move_id).line_ids\
            .filtered(lambda line: line.account_type == 'asset_receivable')\
            .reconcile()
        self.assertIn(invoice.payment_state, ('paid', 'in_payment'), "Invoice not marked as paid after assigning credit.")
