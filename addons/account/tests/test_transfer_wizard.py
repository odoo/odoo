# -*- coding: utf-8 -*-
from odoo import fields, Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged, Form
import time


@tagged('post_install', '-at_install')
class TestTransferWizard(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.company = cls.company_data['company']
        cls.receivable_account = cls.company_data['default_account_receivable']
        cls.payable_account = cls.company_data['default_account_payable']
        cls.accounts = cls.env['account.account'].search([('reconcile', '=', False), ('company_id', '=', cls.company.id)], limit=5)
        cls.journal = cls.company_data['default_journal_misc']

        # Set rate for base currency to 1
        cls.env['res.currency.rate'].search([('company_id', '=', cls.company.id), ('currency_id', '=', cls.company.currency_id.id)]).write({'rate': 1})

        # Create test currencies
        cls.test_currency_1 = cls.env['res.currency'].create({
            'name': "PMK",
            'symbol':'P',
        })

        cls.test_currency_2 = cls.env['res.currency'].create({
            'name': "toto",
            'symbol':'To',
        })

        cls.test_currency_3 = cls.env['res.currency'].create({
            'name': "titi",
            'symbol':'Ti',
        })

        # Create test rates
        cls.env['res.currency.rate'].create({
            'name': time.strftime('%Y') + '-' + '01' + '-01',
            'rate': 0.5,
            'currency_id': cls.test_currency_1.id,
            'company_id': cls.company.id
        })

        cls.env['res.currency.rate'].create({
            'name': time.strftime('%Y') + '-' + '01' + '-01',
            'rate': 2,
            'currency_id': cls.test_currency_2.id,
            'company_id': cls.company.id
        })

        cls.env['res.currency.rate'].create({
            'name': time.strftime('%Y') + '-' + '01' + '-01',
            'rate': 10,
            'currency_id': cls.test_currency_3.id,
            'company_id': cls.company.id
        })

        # Create an account using a foreign currency
        cls.test_currency_account = cls.env['account.account'].create({
            'name': 'test destination account',
            'code': 'test.dest.acc',
            'account_type': 'asset_current',
            'currency_id': cls.test_currency_3.id,
        })

        # Create test account.move
        cls.move_1 = cls.env['account.move'].create({
            'journal_id': cls.journal.id,
            'line_ids': [
                (0, 0, {
                    'name': "test1_1",
                    'account_id': cls.receivable_account.id,
                    'debit': 500,
                }),
                (0, 0, {
                    'name': "test1_2",
                    'account_id': cls.accounts[0].id,
                    'credit': 500,
                }),
                (0, 0, {
                    'name': "test1_3",
                    'account_id': cls.accounts[0].id,
                    'debit': 800,
                    'partner_id': cls.partner_a.id,
                }),
                (0, 0, {
                    'name': "test1_4",
                    'account_id': cls.accounts[1].id,
                    'credit': 500,
                }),
                (0, 0, {
                    'name': "test1_5",
                    'account_id': cls.accounts[2].id,
                    'credit': 300,
                    'partner_id': cls.partner_a.id,
                }),
                (0, 0, {
                    'name': "test1_6",
                    'account_id': cls.accounts[0].id,
                    'debit': 270,
                    'currency_id': cls.test_currency_1.id,
                    'amount_currency': 540,
                }),
                (0, 0, {
                    'name': "test1_7",
                    'account_id': cls.accounts[1].id,
                    'credit': 140,
                }),
                (0, 0, {
                    'name': "test1_8",
                    'account_id': cls.accounts[2].id,
                    'credit': 160,
                }),
                (0, 0, {
                    'name': "test1_9",
                    'account_id': cls.accounts[2].id,
                    'debit': 30,
                    'currency_id': cls.test_currency_2.id,
                    'amount_currency': 15,
                }),
            ]
        })
        cls.move_1.action_post()

        cls.move_2 = cls.env['account.move'].create({
            'journal_id': cls.journal.id,
            'line_ids': [
                (0, 0, {
                    'name': "test2_1",
                    'account_id': cls.accounts[1].id,
                    'debit': 400,
                }),
                (0, 0, {
                    'name': "test2_2",
                    'account_id': cls.payable_account.id,
                    'credit': 400,
                }),
                (0, 0, {
                    'name': "test2_3",
                    'account_id': cls.accounts[3].id,
                    'debit': 250,
                    'partner_id': cls.partner_a.id,
                }),
                (0, 0, {
                    'name': "test2_4",
                    'account_id': cls.accounts[1].id,
                    'debit': 480,
                    'partner_id': cls.partner_b.id,
                }),
                (0, 0, {
                    'name': "test2_5",
                    'account_id': cls.accounts[2].id,
                    'credit': 730,
                    'partner_id': cls.partner_a.id,
                }),
                (0, 0, {
                    'name': "test2_6",
                    'account_id': cls.accounts[2].id,
                    'credit': 412,
                    'partner_id': cls.partner_a.id,
                    'currency_id': cls.test_currency_2.id,
                    'amount_currency': -633,
                }),
                (0, 0, {
                    'name': "test2_7",
                    'account_id': cls.accounts[1].id,
                    'debit': 572,
                }),
                (0, 0, {
                    'name': "test2_8",
                    'account_id': cls.accounts[2].id,
                    'credit': 100,
                    'partner_id': cls.partner_a.id,
                    'currency_id': cls.test_currency_2.id,
                    'amount_currency': -123,
                }),
                (0, 0, {
                    'name': "test2_9",
                    'account_id': cls.accounts[2].id,
                    'credit': 60,
                    'partner_id': cls.partner_a.id,
                    'currency_id': cls.test_currency_1.id,
                    'amount_currency': -10,
                }),
            ]
        })
        cls.move_2.action_post()


    def test_transfer_wizard_reconcile(self):
        """ Tests reconciliation when doing a transfer with the wizard
        """
        active_move_lines = (self.move_1 + self.move_2).mapped('line_ids').filtered(lambda x: x.account_id.account_type in ('asset_receivable', 'liability_payable'))

        # We use a form to pass the context properly to the depends_context move_line_ids field
        context = {'active_model': 'account.move.line', 'active_ids': active_move_lines.ids, 'default_action': 'change_account'}
        with Form(self.env['account.automatic.entry.wizard'].with_context(context)) as wizard_form:
            wizard_form.destination_account_id = self.receivable_account
            wizard_form.journal_id = self.journal
        wizard = wizard_form.save()

        transfer_move_id = wizard.do_action()['res_id']
        transfer_move = self.env['account.move'].browse(transfer_move_id)

        payable_transfer = transfer_move.line_ids.filtered(lambda x: x.account_id == self.payable_account)
        receivable_transfer = transfer_move.line_ids.filtered(lambda x: x.account_id == self.receivable_account)

        self.assertTrue(payable_transfer.reconciled, "Payable line of the transfer move should be fully reconciled")
        self.assertAlmostEqual(self.move_1.line_ids.filtered(lambda x: x.account_id == self.receivable_account).amount_residual, 100, self.company.currency_id.decimal_places, "Receivable line of the original move should be partially reconciled, and still have a residual amount of 100 (500 - 400 from payable account)")
        self.assertTrue(self.move_2.line_ids.filtered(lambda x: x.account_id == self.payable_account).reconciled, "Payable line of the original move should be fully reconciled")
        self.assertAlmostEqual(receivable_transfer.amount_residual, 0, self.company.currency_id.decimal_places, "Receivable line from the transfer move should have nothing left to reconcile")
        self.assertAlmostEqual(payable_transfer.debit, 400, self.company.currency_id.decimal_places, "400 should have been debited from payable account to apply the transfer")
        self.assertAlmostEqual(receivable_transfer.credit, 400, self.company.currency_id.decimal_places, "400 should have been credited to receivable account to apply the transfer")

    def test_transfer_wizard_grouping(self):
        """ Tests grouping (by account and partner) when doing a transfer with the wizard
        """
        active_move_lines = (self.move_1 + self.move_2).mapped('line_ids').filtered(lambda x: x.name in ('test1_3', 'test1_4', 'test1_5', 'test2_3', 'test2_4', 'test2_5', 'test2_6', 'test2_8'))

        # We use a form to pass the context properly to the depends_context move_line_ids field
        context = {'active_model': 'account.move.line', 'active_ids': active_move_lines.ids, 'default_action': 'change_account'}
        with Form(self.env['account.automatic.entry.wizard'].with_context(context)) as wizard_form:
            wizard_form.destination_account_id = self.accounts[4]
            wizard_form.journal_id = self.journal
        wizard = wizard_form.save()

        transfer_move_id = wizard.do_action()['res_id']
        transfer_move = self.env['account.move'].browse(transfer_move_id)

        groups = {}
        for line in transfer_move.line_ids:
            key = (line.account_id, line.partner_id or None, line.currency_id)
            self.assertFalse(groups.get(key), "There should be only one line per (account, partner, currency) group in the transfer move.")
            groups[key] = line

        self.assertAlmostEqual(groups[(self.accounts[0], self.partner_a, self.company_data['currency'])].balance, -800, self.company.currency_id.decimal_places)
        self.assertAlmostEqual(groups[(self.accounts[1], None, self.company_data['currency'])].balance, 500, self.company.currency_id.decimal_places)
        self.assertAlmostEqual(groups[(self.accounts[1], self.partner_b, self.company_data['currency'])].balance, -480, self.company.currency_id.decimal_places)
        self.assertAlmostEqual(groups[(self.accounts[2], self.partner_a, self.company_data['currency'])].balance, 1030, self.company.currency_id.decimal_places)
        self.assertAlmostEqual(groups[(self.accounts[2], self.partner_a, self.test_currency_2)].balance, 512, self.company.currency_id.decimal_places)
        self.assertAlmostEqual(groups[(self.accounts[3], self.partner_a, self.company_data['currency'])].balance, -250, self.company.currency_id.decimal_places)


    def test_transfer_wizard_currency_conversion(self):
        """ Tests multi currency use of the transfer wizard, checking the conversion
        is propperly done when using a destination account with a currency_id set.
        """
        active_move_lines = self.move_1.mapped('line_ids').filtered(lambda x: x.name in ('test1_6', 'test1_9'))

        # We use a form to pass the context properly to the depends_context move_line_ids field
        context = {'active_model': 'account.move.line', 'active_ids': active_move_lines.ids, 'default_action': 'change_account'}
        with Form(self.env['account.automatic.entry.wizard'].with_context(context)) as wizard_form:
            wizard_form.destination_account_id = self.test_currency_account
            wizard_form.journal_id = self.journal
        wizard = wizard_form.save()

        transfer_move_id = wizard.do_action()['res_id']
        transfer_move = self.env['account.move'].browse(transfer_move_id)

        destination_line = transfer_move.line_ids.filtered(lambda x: x.account_id == self.test_currency_account)
        self.assertEqual(destination_line.currency_id, self.test_currency_3, "Transferring to an account with a currency set should keep this currency on the transfer line.")
        self.assertAlmostEqual(destination_line.amount_currency, 3000, self.company.currency_id.decimal_places, "Transferring two lines with different currencies (and the same partner) on an account with a currency set should convert the balance of these lines into this account's currency (here (270 + 30) * 10 = 3000)")


    def test_transfer_wizard_no_currency_conversion(self):
        """ Tests multi currency use of the transfer wizard, verifying that
        currency amounts are kept on distinct lines when transferring to an
        account without any currency specified.
        """
        active_move_lines = self.move_2.mapped('line_ids').filtered(lambda x: x.name in ('test2_9', 'test2_6', 'test2_8'))

        # We use a form to pass the context properly to the depends_context move_line_ids field
        context = {'active_model': 'account.move.line', 'active_ids': active_move_lines.ids, 'default_action': 'change_account'}
        with Form(self.env['account.automatic.entry.wizard'].with_context(context)) as wizard_form:
            wizard_form.destination_account_id = self.receivable_account
            wizard_form.journal_id = self.journal
        wizard = wizard_form.save()

        transfer_move_id = wizard.do_action()['res_id']
        transfer_move = self.env['account.move'].browse(transfer_move_id)

        destination_lines = transfer_move.line_ids.filtered(lambda x: x.account_id == self.receivable_account)
        self.assertEqual(len(destination_lines), 2, "Two lines should have been created on destination account: one for each currency (the lines with same partner and currency should have been aggregated)")
        self.assertAlmostEqual(destination_lines.filtered(lambda x: x.currency_id == self.test_currency_1).amount_currency, -10, self.test_currency_1.decimal_places)
        self.assertAlmostEqual(destination_lines.filtered(lambda x: x.currency_id == self.test_currency_2).amount_currency, -756, self.test_currency_2.decimal_places)

    def test_period_change_lock_date(self):
        """ Test that the period change wizard correctly handles the lock date: if the original entry is dated
        before the lock date, the adjustment entry is created on the first end of month after the lock date.
        """
        # Set up accrual accounts
        self.company_data['company'].expense_accrual_account_id = self.env['account.account'].create({
            'name': 'Expense Accrual Account',
            'code': '113226',
            'account_type': 'asset_prepayments',
            'reconcile': True,
        })
        self.company_data['company'].revenue_accrual_account_id = self.env['account.account'].create({
            'name': 'Revenue Accrual Account',
            'code': '226113',
            'account_type': 'liability_current',
            'reconcile': True,
        })

        # Create a move before the lock date
        move = self.env['account.move'].create({
            'journal_id': self.company_data['default_journal_sale'].id,
            'date': '2019-01-01',
            'line_ids': [
                Command.create({'account_id': self.accounts[0].id, 'debit': 1000, }),
                Command.create({'account_id': self.accounts[0].id, 'credit': 1000, }),
            ]
        })
        move.action_post()

        # Set the lock date
        move.company_id.write({'period_lock_date': '2019-02-28', 'fiscalyear_lock_date': '2019-02-28'})

        # Open the transfer wizard at a date after the lock date
        wizard = self.env['account.automatic.entry.wizard'] \
            .with_context(active_model='account.move.line', active_ids=move.line_ids[0].ids) \
            .create({
                'action': 'change_period',
                'date': '2019-05-01',
                'journal_id': self.company_data['default_journal_misc'].id,
            })

        # Check that the 'The date is being set prior to the user lock date' message appears.
        self.assertRecordValues(wizard, [{
            'lock_date_message': 'The date is being set prior to the user lock date 02/28/2019. '
                                 'The Journal Entry will be accounted on 03/31/2019 upon posting.'
        }])

        # Create the adjustment move.
        wizard_res = wizard.do_action()

        # Check that the adjustment move was created on the first end of month after the lock date.
        created_moves = self.env['account.move'].browse(wizard_res['domain'][0][2])
        adjustment_move = created_moves[1]  # There are 2 created moves; the adjustment move is the second one.
        self.assertRecordValues(adjustment_move, [{'date': fields.Date.to_date('2019-03-31')}])
