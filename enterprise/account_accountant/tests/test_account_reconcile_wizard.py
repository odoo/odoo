import re

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestAccountReconcileWizard(AccountTestInvoicingCommon):
    """ Tests the account reconciliation and its wizard. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.receivable_account = cls.company_data['default_account_receivable']
        cls.payable_account = cls.company_data['default_account_payable']
        cls.revenue_account = cls.company_data['default_account_revenue']
        cls.payable_account_2 = cls.env['account.account'].create({
            'name': 'Payable Account 2',
            'account_type': 'liability_current',
            'code': 'PAY2.TEST',
            'reconcile': True
        })
        cls.write_off_account = cls.env['account.account'].create({
            'name': 'Write-Off Account',
            'account_type': 'liability_current',
            'code': 'WO.TEST',
            'reconcile': False
        })

        cls.misc_journal = cls.company_data['default_journal_misc']
        cls.test_date = fields.Date.from_string('2016-01-01')
        cls.company_currency = cls.company_data['currency']
        cls.foreign_currency = cls.setup_other_currency('EUR')
        cls.foreign_currency_2 = cls.setup_other_currency('XAF', rates=[('2016-01-01', 6.0), ('2017-01-01', 4.0)])

        cls.tax_recover_account_id = cls.env['account.account'].create({
            'name': 'Tax Account Test',
            'account_type': 'liability_current',
            'code': 'TAX.TEST',
            'reconcile': False
        })
        cls.base_tag = cls.env['account.account.tag'].create({
            'applicability': 'taxes',
            'name': 'base_tax_tag',
            'country_id': cls.company_data['company'].country_id.id,
        })
        cls.tax_tag = cls.env['account.account.tag'].create({
            'applicability': 'taxes',
            'name': 'tax_tax_tag',
            'country_id': cls.company_data['company'].country_id.id,
        })
        cls.tax_id = cls.env['account.tax'].create({
            'name': 'tax_test',
            'amount_type': 'percent',
            'amount': 25.0,
            'type_tax_use': 'sale',
            'company_id': cls.company_data['company'].id,
            'invoice_repartition_line_ids': [
                Command.create({'factor_percent': 100, 'repartition_type': 'base', 'tag_ids': [Command.set(cls.base_tag.ids)]}),
                Command.create({'factor_percent': 100, 'account_id': cls.tax_recover_account_id.id,
                                'tag_ids': [Command.set(cls.tax_tag.ids)]}),
            ],
            'refund_repartition_line_ids': [
                Command.create({'factor_percent': 100, 'repartition_type': 'base', 'tag_ids': [Command.set(cls.base_tag.ids)]}),
                Command.create({'factor_percent': 100, 'account_id': cls.tax_recover_account_id.id,
                                'tag_ids': [Command.set(cls.tax_tag.ids)]}),
            ],
        })

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------
    def assertWizardReconcileValues(self, selected_lines, input_values, wo_expected_values, expected_transfer_values=None):
        wizard = self.env['account.reconcile.wizard'].with_context(
            active_model='account.move.line',
            active_ids=selected_lines.ids,
        ).new(input_values)
        if expected_transfer_values:
            transfer_move = wizard.create_transfer()
            # transfer move values
            self.assertRecordValues(transfer_move.line_ids.sorted('balance'), expected_transfer_values)
            # transfer warning message
            self.assertTrue(wizard.transfer_warning_message)
            regex_match = re.findall(r'([+-]*\d*,*\d+\.*\d+)', wizard.transfer_warning_message)
            # match transferred amount
            self.assertEqual(
                float(regex_match[0].replace(',', '')),
                transfer_move.amount_total_in_currency_signed or transfer_move.amount_total_signed
            )
            transfer_from_account = transfer_move.line_ids.filtered(lambda aml: 'Transfer from' in aml.name).account_id
            transfer_to_account = transfer_move.line_ids.account_id - transfer_from_account
            transfer_from_amls = transfer_move.line_ids.filtered(lambda aml: aml.account_id == transfer_from_account)
            transfer_amount = sum(aml.balance for aml in transfer_from_amls)
            # match account codes
            if transfer_amount > 0:
                self.assertEqual(regex_match[1:], [transfer_from_account.code, transfer_to_account.code])
            else:
                self.assertEqual(regex_match[1:], [transfer_to_account.code, transfer_from_account.code])
        write_off_move = wizard.create_write_off()
        self.assertRecordValues(write_off_move.line_ids.sorted('balance'), wo_expected_values)
        wizard.reconcile()
        if wizard.allow_partials or (
            wizard.edit_mode
            and wizard.reco_currency_id.compare_amounts(wizard.edit_mode_amount_currency, wizard.amount_currency)
        ):
            # partial reconcile
            self.assertTrue(len(selected_lines.matched_debit_ids) > 0 or len(selected_lines.matched_credit_ids) > 0)
        else:
            # full reconcile
            self.assertTrue(selected_lines.full_reconcile_id)
            self.assertRecordValues(
                selected_lines,
                [{'amount_residual': 0.0, 'amount_residual_currency': 0.0, 'reconciled': True}] * len(selected_lines),
            )

    # -------------------------------------------------------------------------
    # TESTS
    # -------------------------------------------------------------------------
    def test_wizard_should_not_open(self):
        """ Test that when we reconcile two lines that belong to the same account and have a 0 balance should
        reconcile silently and not open the write-off wizard.
        """
        line_1 = self.create_line_for_reconciliation(1000.0, 1000.0, self.company_currency, '2016-01-01')
        line_2 = self.create_line_for_reconciliation(-1000.0, -1000.0, self.company_currency, '2016-01-01')
        (line_1 + line_2).action_reconcile()
        self.assertRecordValues(
            line_1 + line_2,
            [{'amount_residual': 0.0, 'amount_residual_currency': 0.0, 'reconciled': True}] * 2
        )

    def test_wizard_should_open(self):
        """ Test that when a write-off is required (because of transfer or non-zero balance) the wizard opens. """
        line_1 = self.create_line_for_reconciliation(1000.0, 1000.0, self.company_currency, '2016-01-01')
        line_2 = self.create_line_for_reconciliation(-500.0, -500.0, self.company_currency, '2016-01-01')
        line_3 = self.create_line_for_reconciliation(-500.0, -1500.0, self.foreign_currency, '2016-01-01')
        line_4 = self.create_line_for_reconciliation(-900.0, -900.0, self.company_currency, '2016-01-01', account_1=self.payable_account)
        for batch, sub_test_name in (
                (line_1 + line_2, 'Batch with non-zero balance in company currency'),
                (line_1 + line_3, 'Batch with non-zero balance in foreign currency'),
                (line_1 + line_4, 'Batch with different accounts'),
        ):
            with self.subTest(sub_test_name=sub_test_name):
                returned_action = batch.action_reconcile()
                self.assertEqual(returned_action.get('res_model'), 'account.reconcile.wizard')

    def test_reconcile_silently_same_account(self):
        """ When balance is 0 we can silently reconcile items. """
        line_1 = self.create_line_for_reconciliation(1000.0, 1000.0, self.company_currency, '2016-01-01')
        line_2 = self.create_line_for_reconciliation(-1000.0, -1000.0, self.company_currency, '2016-01-01')
        lines = (line_1 + line_2)
        lines.action_reconcile()
        self.assertTrue(lines.full_reconcile_id)
        self.assertRecordValues(
            lines,
            [{'amount_residual': 0.0, 'amount_residual_currency': 0.0, 'reconciled': True}] * len(lines),
        )

    def test_reconcile_silently_transfer(self):
        """ When balance is 0, and we need a transfer, we do the transfer+reconcile silently. """
        line_1 = self.create_line_for_reconciliation(1000.0, 1000.0, self.company_currency, '2016-01-01')
        line_2 = self.create_line_for_reconciliation(-1000.0, -1000.0, self.company_currency, '2016-01-01', account_1=self.payable_account)
        lines = (line_1 + line_2)
        lines.action_reconcile()
        self.assertTrue(lines.full_reconcile_id)
        self.assertRecordValues(
            lines,
            [{'amount_residual': 0.0, 'amount_residual_currency': 0.0, 'reconciled': True}] * len(lines),
        )

    def test_write_off_same_currency(self):
        """ Reconciliation of two lines with no transfer/foreign currencies/taxes/reco models."""
        line_1 = self.create_line_for_reconciliation(1000.0, 1000.0, self.company_currency, '2016-01-01')
        line_2 = self.create_line_for_reconciliation(-500.0, -500.0, self.company_currency, '2016-01-01')
        wizard_input_values = {
            'journal_id': self.misc_journal.id,
            'account_id': self.write_off_account.id,
            'label': 'Write-Off Test Label',
            'allow_partials': False,
            'date': self.test_date,
        }
        write_off_expected_values = [
            {'account_id': self.receivable_account.id, 'name': 'Write-Off Test Label', 'balance': -500.0},
            {'account_id': self.write_off_account.id, 'name': 'Write-Off Test Label', 'balance': 500.0},
        ]
        self.assertWizardReconcileValues(line_1 + line_2, wizard_input_values, write_off_expected_values)

    def test_write_off_one_foreign_currency(self):
        """ Reconciliation of two lines with one of the two using foreign currency should reconcile in foreign currency."""
        line_1 = self.create_line_for_reconciliation(1000.0, 1000.0, self.company_currency, '2016-01-01')
        line_2 = self.create_line_for_reconciliation(-500.0, -1500.0, self.foreign_currency, '2016-01-01')
        wizard_input_values = {
            'journal_id': self.misc_journal.id,
            'account_id': self.write_off_account.id,
            'label': 'Write-Off Test Label',
            'allow_partials': False,
            'date': self.test_date,
        }
        expected_values = [
            {'account_id': self.receivable_account.id, 'name': 'Write-Off Test Label',
             'balance': -500.0, 'amount_currency': -1500.0, 'currency_id': self.foreign_currency.id},
            {'account_id': self.write_off_account.id, 'name': 'Write-Off Test Label',
             'balance': 500.0, 'amount_currency': 1500.0, 'currency_id': self.foreign_currency.id},
        ]
        self.assertWizardReconcileValues(line_1 + line_2, wizard_input_values, expected_values)

    def test_write_off_one_foreign_currency_rounding(self):
        """ Reconciliation of two lines with one of the two using foreign currency should reconcile in foreign currency."""
        foreign_currency = self.setup_other_currency('CAD', rounding=0.01, rates=[('2016-01-01', 0.052972554919), ('2017-01-01', 4.0)])

        # Check that the reconciliation works independently of
        # - whether the foreign amount is debit or credit
        # - the account type (payable / receivable)
        self.assertFalse(self.payable_account_2.account_type in ('asset_receivable', 'liability_payable'))
        self.assertTrue(self.receivable_account.account_type in ('asset_receivable', 'liability_payable'))
        for foreign_amount_sign, account in [
            (-1, self.payable_account_2),
            (1, self.payable_account_2),
            (-1, self.receivable_account),
            (1, self.receivable_account),
        ]:
            with self.subTest(sub_test_name=f'sign: {foreign_amount_sign}, account: {account.name}'):
                line_1 = self.create_line_for_reconciliation(
                    -foreign_amount_sign * 372239.38, -foreign_amount_sign * 372239.38, self.company_currency,
                    '2016-01-01', account_1=account,
                )
                line_2 = self.create_line_for_reconciliation(
                    foreign_amount_sign * 377554.0, foreign_amount_sign * 20000.0, foreign_currency,
                    '2016-01-01', account_1=account,
                )
                lines = line_1 + line_2

                # Test the opening of the wizard without input values
                wizard = self.env['account.reconcile.wizard'].with_context(
                    active_model='account.move.line',
                    active_ids=lines.ids,
                ).new()
                self.assertRecordValues(wizard, [{
                    'is_write_off_required': True,
                    'amount': foreign_amount_sign * 5314.62,
                    'amount_currency': foreign_amount_sign * 281.53,
                    'reco_currency_id': foreign_currency.id,
                }])

                # Check the created write-off move and that there is no residual
                wizard_input_values = {
                    'journal_id': self.misc_journal.id,
                    'account_id': self.write_off_account.id,
                    'label': 'Write-Off Test Label',
                    'allow_partials': False,
                    'date': self.test_date,
                }
                # We sort the expected values the same way as `assertWizardReconcileValues` sorts the lines
                expected_values = sorted([
                    {'account_id': account.id, 'name': 'Write-Off Test Label',
                     'balance': -foreign_amount_sign * 5314.62,
                     'amount_currency': -foreign_amount_sign * 281.53, 'currency_id': foreign_currency.id},
                    {'account_id': self.write_off_account.id, 'name': 'Write-Off Test Label',
                     'balance': foreign_amount_sign * 5314.62,
                     'amount_currency': foreign_amount_sign * 281.53, 'currency_id': foreign_currency.id},
                ], key=lambda vals: vals['balance'])
                self.assertWizardReconcileValues(lines, wizard_input_values, expected_values)

                full_reconcile = lines.full_reconcile_id
                self.assertTrue(full_reconcile)
                self.assertFalse(full_reconcile.exchange_move_id)

    def test_write_off_mixed_foreign_currencies(self):
        """ Write off with multiple currencies should reconcile in company currency."""
        line_1 = self.create_line_for_reconciliation(1000.0, 1000.0, self.company_currency, '2016-01-01')
        line_2 = self.create_line_for_reconciliation(-500.0, -1500.0, self.foreign_currency, '2016-01-01')
        line_3 = self.create_line_for_reconciliation(-400.0, -2400.0, self.foreign_currency_2, '2016-01-01')
        wizard_input_values = {
            'journal_id': self.misc_journal.id,
            'account_id': self.write_off_account.id,
            'label': 'Write-Off Test Label',
            'allow_partials': False,
            'date': self.test_date,
        }
        expected_values = [
            {'account_id': self.receivable_account.id, 'name': 'Write-Off Test Label',
             'balance': -100.0, 'amount_currency': -100.0, 'currency_id': self.company_currency.id},
            {'account_id': self.write_off_account.id, 'name': 'Write-Off Test Label',
             'balance': 100.0, 'amount_currency': 100.0, 'currency_id': self.company_currency.id},
        ]
        self.assertWizardReconcileValues(line_1 + line_2 + line_3, wizard_input_values, expected_values)

    def test_write_off_one_foreign_currency_change_rate(self):
        """ Tests that write-off use the correct rate from/at wizard's date. """
        foreign_currency = self.setup_other_currency('CAD', rounding=0.001, rates=[('2016-01-01', 0.5), ('2017-01-01', 1 / 3)])
        new_date = fields.Date.from_string('2017-02-01')
        line_1 = self.create_line_for_reconciliation(-2000.0, -2000.0, self.company_currency, '2017-01-01')  # conversion in 2017 => -666.67🍫
        line_2 = self.create_line_for_reconciliation(2000.0, 1000.0, foreign_currency, '2016-01-01')
        wizard_input_values = {
            'journal_id': self.misc_journal.id,
            'account_id': self.write_off_account.id,
            'label': 'Write-Off Test Label',
            'allow_partials': False,
            'date': new_date,
        }
        expected_values = [
            {'account_id': self.receivable_account.id, 'name': 'Write-Off Test Label',
             'balance': -1000.0, 'amount_currency': -333.333, 'currency_id': foreign_currency.id},
            {'account_id': self.write_off_account.id, 'name': 'Write-Off Test Label',
             'balance': 1000.0, 'amount_currency': 333.333, 'currency_id': foreign_currency.id},
        ]
        self.assertWizardReconcileValues(line_1 + line_2, wizard_input_values, expected_values)

    def test_write_off_mixed_foreign_currencies_change_rate(self):
        """ Tests that write-off use the correct rate from/at wizard's date. """
        new_date = fields.Date.from_string('2017-02-01')
        line_1 = self.create_line_for_reconciliation(1000.0, 1000.0, self.company_currency, '2016-01-01')
        line_2 = self.create_line_for_reconciliation(-500.0, -1500.0, self.foreign_currency, '2016-01-01')
        line_3 = self.create_line_for_reconciliation(-400.0, -2400.0, self.foreign_currency_2, '2016-01-01')
        wizard_input_values = {
            'journal_id': self.misc_journal.id,
            'account_id': self.write_off_account.id,
            'label': 'Write-Off Test Label',
            'allow_partials': False,
            'date': new_date,
        }
        expected_values = [
            {'account_id': self.receivable_account.id, 'name': 'Write-Off Test Label',
             'balance': -100.0, 'amount_currency': -100.0, 'currency_id': self.company_currency.id},
            {'account_id': self.write_off_account.id, 'name': 'Write-Off Test Label',
             'balance': 100.0, 'amount_currency': 100.0, 'currency_id': self.company_currency.id},
        ]
        self.assertWizardReconcileValues(line_1 + line_2 + line_3, wizard_input_values, expected_values)

    def test_write_off_both_same_foreign_currency_ensure_no_exchange_diff(self):
        """ Test that if both AMLs have the same foreign currency and rate, the amount in company currency
            is computed on the write-off in such a way that no exchange diff is created.
        """
        foreign_currency = self.setup_other_currency('CAD', rounding=0.01, rates=[('2016-01-01', 1 / 0.225)])
        new_date = fields.Date.from_string('2017-02-01')
        line_1 = self.create_line_for_reconciliation(21.38, 95.0, foreign_currency, '2016-01-01')
        line_2 = self.create_line_for_reconciliation(1.13, 5.0, foreign_currency, '2016-01-01')
        line_3 = self.create_line_for_reconciliation(1.13, 5.0, foreign_currency, '2016-01-01')
        wizard_input_values = {
            'journal_id': self.misc_journal.id,
            'account_id': self.write_off_account.id,
            'label': 'Write-Off Test Label',
            'allow_partials': False,
            'date': new_date,
        }
        expected_values = [
            {'account_id': self.receivable_account.id, 'name': 'Write-Off Test Label',
             'balance': -23.64, 'amount_currency': -105.0, 'currency_id': foreign_currency.id},
            {'account_id': self.write_off_account.id, 'name': 'Write-Off Test Label',
             'balance': 23.64, 'amount_currency': 105.0, 'currency_id': foreign_currency.id},
        ]
        self.assertWizardReconcileValues(line_1 + line_2 + line_3, wizard_input_values, expected_values)

    def test_write_off_with_transfer_account_same_currency(self):
        line_1 = self.create_line_for_reconciliation(1000.0, 1000.0, self.company_currency, '2016-01-01')
        line_2 = self.create_line_for_reconciliation(100.0, 100.0, self.company_currency, '2016-01-01', account_1=self.payable_account)
        wizard_input_values = {
            'journal_id': self.misc_journal.id,
            'account_id': self.write_off_account.id,
            'label': 'Write-Off Test Label',
            'allow_partials': False,
            'date': self.test_date,
        }
        expected_transfer_values = [
            {'account_id': self.payable_account.id, 'name': f'Transfer to {self.receivable_account.display_name}',
             'balance': -100.0, 'amount_currency': -100.0, 'currency_id': self.company_currency.id},
            {'account_id': self.receivable_account.id, 'name': f'Transfer from {self.payable_account.display_name}',
             'balance': 100.0, 'amount_currency': 100.0, 'currency_id': self.company_currency.id},
        ]
        expected_values = [
            {'account_id': self.receivable_account.id, 'name': 'Write-Off Test Label',
             'balance': -1100.0, 'amount_currency': -1100.0, 'currency_id': self.company_currency.id},
            {'account_id': self.write_off_account.id, 'name': 'Write-Off Test Label',
             'balance': 1100.0, 'amount_currency': 1100.0, 'currency_id': self.company_currency.id},
        ]
        self.assertWizardReconcileValues(line_1 + line_2, wizard_input_values, expected_values, expected_transfer_values=expected_transfer_values)

    def test_write_off_with_transfer_account_one_foreign_currency(self):
        line_1 = self.create_line_for_reconciliation(1100.0, 1100.0, self.company_currency, '2016-01-01')
        line_2 = self.create_line_for_reconciliation(100.0, 300.0, self.foreign_currency, '2016-01-01', account_1=self.payable_account)
        wizard_input_values = {
            'journal_id': self.misc_journal.id,
            'account_id': self.write_off_account.id,
            'label': 'Write-Off Test Label',
            'allow_partials': False,
            'date': self.test_date,
        }
        expected_transfer_values = [
            {'account_id': self.payable_account.id, 'name': f'Transfer to {self.receivable_account.display_name}',
             'balance': -100.0, 'amount_currency': -300.0, 'currency_id': self.foreign_currency.id},
            {'account_id': self.receivable_account.id, 'name': f'Transfer from {self.payable_account.display_name}',
             'balance': 100.0, 'amount_currency': 300.0, 'currency_id': self.foreign_currency.id},
        ]
        expected_values = [
            {'account_id': self.receivable_account.id, 'name': 'Write-Off Test Label',
             'balance': -1200.0, 'amount_currency': -3600.0, 'currency_id': self.foreign_currency.id},
            {'account_id': self.write_off_account.id, 'name': 'Write-Off Test Label',
             'balance': 1200.0, 'amount_currency': 3600.0, 'currency_id': self.foreign_currency.id},
        ]
        self.assertWizardReconcileValues(line_1 + line_2, wizard_input_values, expected_values, expected_transfer_values=expected_transfer_values)

    def test_write_off_with_complex_transfer(self):
        partner_1 = self.env['res.partner'].create({'name': 'Test Partner 1'})
        partner_2 = self.env['res.partner'].create({'name': 'Test Partner 2'})
        line_1 = self.create_line_for_reconciliation(1000.0, 1000.0, self.company_currency, '2016-01-01', partner=partner_2)
        line_2 = self.create_line_for_reconciliation(-100.0, -300.0, self.foreign_currency, '2016-01-01', account_1=self.payable_account, partner=partner_1)
        line_3 = self.create_line_for_reconciliation(-200.0, -200.0, self.company_currency, '2016-01-01', account_1=self.payable_account, partner=partner_2)
        line_4 = self.create_line_for_reconciliation(-200.0, -600.0, self.foreign_currency, '2016-01-01', account_1=self.payable_account, partner=partner_2)
        line_5 = self.create_line_for_reconciliation(-200.0, -600.0, self.foreign_currency, '2016-01-01', account_1=self.payable_account, partner=partner_2)
        wizard_input_values = {
            'journal_id': self.misc_journal.id,
            'account_id': self.write_off_account.id,
            'label': 'Write-Off Test Label',
            'allow_partials': False,
            'date': self.test_date,
        }
        expected_transfer_values = [
            {'account_id': self.receivable_account.id, 'name': f'Transfer from {self.payable_account.display_name}',
             'balance': -400.0, 'amount_currency': -1200.0, 'currency_id': self.foreign_currency.id, 'partner_id': partner_2.id},
            {'account_id': self.receivable_account.id, 'name': f'Transfer from {self.payable_account.display_name}',
             'balance': -200.0, 'amount_currency': -200.0, 'currency_id': self.company_currency.id, 'partner_id': partner_2.id},
            {'account_id': self.receivable_account.id, 'name': f'Transfer from {self.payable_account.display_name}',
             'balance': -100.0, 'amount_currency': -300.0, 'currency_id': self.foreign_currency.id, 'partner_id': partner_1.id},
            {'account_id': self.payable_account.id, 'name': f'Transfer to {self.receivable_account.display_name}',
             'balance': 100.0, 'amount_currency': 300.0, 'currency_id': self.foreign_currency.id, 'partner_id': partner_1.id},
            {'account_id': self.payable_account.id, 'name': f'Transfer to {self.receivable_account.display_name}',
             'balance': 200.0, 'amount_currency': 200.0, 'currency_id': self.company_currency.id, 'partner_id': partner_2.id},
            {'account_id': self.payable_account.id, 'name': f'Transfer to {self.receivable_account.display_name}',
             'balance': 400.0, 'amount_currency': 1200.0, 'currency_id': self.foreign_currency.id, 'partner_id': partner_2.id},
        ]
        expected_values = [
            {'account_id': self.receivable_account.id, 'name': 'Write-Off Test Label',
             'balance': -300.0, 'amount_currency': -900.0, 'currency_id': self.foreign_currency.id},
            {'account_id': self.write_off_account.id, 'name': 'Write-Off Test Label',
             'balance': 300.0, 'amount_currency': 900.0, 'currency_id': self.foreign_currency.id},
        ]
        self.assertWizardReconcileValues(line_1 + line_2 + line_3 + line_4 + line_5, wizard_input_values, expected_values, expected_transfer_values=expected_transfer_values)

    def test_write_off_with_tax(self):
        """ Tests write-off with a tax set on the wizard. """
        line_1 = self.create_line_for_reconciliation(1000.0, 1000.0, self.company_currency, '2016-01-01')
        line_2 = self.create_line_for_reconciliation(-500.0, -500.0, self.company_currency, '2016-01-01')
        wizard_input_values = {
            'journal_id': self.misc_journal.id,
            'account_id': self.write_off_account.id,
            'label': 'Write-Off Test Label',
            'tax_id': self.tax_id.id,
            'allow_partials': False,
            'date': self.test_date,
        }
        write_off_expected_values = [
            {'account_id': self.receivable_account.id, 'name': 'Write-Off Test Label', 'balance': -500.0},
            {'account_id': self.tax_recover_account_id.id, 'name': f'{self.tax_id.name}', 'balance': 100.0},
            {'account_id': self.write_off_account.id, 'name': 'Write-Off Test Label', 'balance': 400.0},
        ]
        self.assertWizardReconcileValues(line_1 + line_2, wizard_input_values, write_off_expected_values)

    def test_write_off_tax_tag_invert(self):
        """Tests that write off set the invert tag correctly"""
        line_1 = self.create_line_for_reconciliation(-100.0, -100.0, self.company_currency, '2025-01-01')
        account = self.company_data['default_account_expense']
        wizard_input_values = {
            'journal_id': self.misc_journal.id,
            'account_id': account.id,
            'label': 'Write-Off Test Label',
            'tax_id': self.tax_id.id,
            'allow_partials': False,
            'date': self.test_date,
        }
        write_off_expected_values = [
            {'account_id': account.id, 'balance': -80.0, 'tax_tag_invert': True},
            {'account_id': self.tax_recover_account_id.id, 'balance': -20.0, 'tax_tag_invert': True},
            {'account_id': self.receivable_account.id, 'balance': 100, 'tax_tag_invert': False},
        ]
        self.assertWizardReconcileValues(line_1, wizard_input_values, write_off_expected_values)

    def test_write_off_tax_reverse_charge(self):
        """
        With revert charges, we should consider the price as excluded when reconciling
        """
        self.tax_id.write({
            'invoice_repartition_line_ids': [Command.create({'factor_percent': -100, 'account_id': self.tax_recover_account_id.id})],
            'refund_repartition_line_ids': [Command.create({'factor_percent': -100, 'account_id': self.tax_recover_account_id.id})],
        })
        line_1 = self.create_line_for_reconciliation(100.0, 100.0, self.company_currency, '2025-01-01')
        account = self.company_data['default_account_expense']
        wizard_input_values = {
            'journal_id': self.misc_journal.id,
            'account_id': account.id,
            'label': 'Write-Off Test Label',
            'tax_id': self.tax_id.id,
            'allow_partials': False,
            'date': self.test_date,
        }
        write_off_expected_values = [
            {'account_id': self.receivable_account.id, 'balance': -100.0},
            {'account_id': self.tax_recover_account_id.id, 'balance': -25.0},
            {'account_id': self.tax_recover_account_id.id, 'balance': 25.0},
            {'account_id': account.id, 'balance': 100},
        ]
        self.assertWizardReconcileValues(line_1, wizard_input_values, write_off_expected_values)

    def test_reconcile_partials_allowed(self):
        line_1 = self.create_line_for_reconciliation(1000.0, 1000.0, self.company_currency, '2016-01-01')
        line_2 = self.create_line_for_reconciliation(-500.0, -500.0, self.company_currency, '2016-01-01')
        lines = line_1 + line_2
        wizard_input_values = {
            'allow_partials': True,
        }
        wizard = self.env['account.reconcile.wizard'].with_context(
            active_model='account.move.line',
            active_ids=lines.ids,
        ).new(wizard_input_values)
        wizard.reconcile()
        self.assertTrue(len(lines.matched_debit_ids) > 0 or len(lines.matched_credit_ids) > 0)

    def test_raise_lock_date_violation(self):
        """ If a write-off violates the lock date we display a banner and change the date afterwards. """
        company_id = self.company_data['company']
        company_id.fiscalyear_lock_date = fields.Date.from_string('2016-12-01')
        line_1 = self.create_line_for_reconciliation(1000.0, 1000.0, self.company_currency, '2016-06-01')
        line_2 = self.create_line_for_reconciliation(-500.0, -500.0, self.company_currency, '2016-06-01')
        wizard = self.env['account.reconcile.wizard'].with_context(
            active_model='account.move.line',
            active_ids=(line_1 + line_2).ids,
        ).new({'date': self.test_date})
        self.assertTrue(bool(wizard.lock_date_violated_warning_message))

    def test_raise_reconcile_too_many_accounts(self):
        """ If you try to reconcile lines from more than 2 accounts, it should raise an error. """
        line_1 = self.create_line_for_reconciliation(1000.0, 1000.0, self.company_currency, '2016-01-01')
        line_2 = self.create_line_for_reconciliation(-500.0, -500.0, self.company_currency, '2016-01-01', account_1=self.payable_account)
        line_3 = self.create_line_for_reconciliation(-500.0, -500.0, self.company_currency, '2016-01-01', account_1=self.payable_account_2)
        with self.assertRaises(UserError):
            (line_1 + line_2 + line_3).action_reconcile()

    def test_reconcile_no_receivable_no_payable_account(self):
        """ If you try to reconcile lines in an account that is neither from payable nor receivable
        it should reconcile in company currency.
        """
        account = self.company_data['default_account_expense']
        account.reconcile = True
        line_1 = self.create_line_for_reconciliation(1000.0, 1000.0, self.company_currency, '2016-01-01', account_1=account)
        line_2 = self.create_line_for_reconciliation(-500.0, -1500.0, self.foreign_currency, '2016-01-01', account_1=account)
        wizard_input_values = {
            'journal_id': self.misc_journal.id,
            'account_id': self.write_off_account.id,
            'label': 'Write-Off Test Label',
            'allow_partials': False,
            'date': self.test_date,
        }
        expected_values = [
            {'account_id': account.id, 'name': 'Write-Off Test Label',
             'balance': -500.0, 'amount_currency': -500.0, 'currency_id': self.company_currency.id},
            {'account_id': self.write_off_account.id, 'name': 'Write-Off Test Label',
             'balance': 500.0, 'amount_currency': 500.0, 'currency_id': self.company_currency.id},
        ]
        self.assertWizardReconcileValues(line_1 + line_2, wizard_input_values, expected_values)

    def test_reconcile_exchange_diff_foreign_currency(self):
        """ When reconciling exchange_diff with amount_residual_currency = 0 we need to reconcile in company_currency.
        """
        exchange_gain_account = self.company_data['company'].income_currency_exchange_account_id
        exchange_gain_account.reconcile = True
        line_1 = self.create_line_for_reconciliation(150.0, 0.0, self.foreign_currency, '2016-01-01')
        line_2 = self.create_line_for_reconciliation(-100.0, 0.0, self.foreign_currency, '2016-01-01', account_1=exchange_gain_account)
        wizard_input_values = {
            'journal_id': self.misc_journal.id,
            'account_id': self.write_off_account.id,
            'label': 'Write-Off Test Label',
            'allow_partials': False,
            'date': self.test_date,
        }
        # Note the transfer will always be in the currency of the line transferred
        expected_transfer_values = [
            {'account_id': self.receivable_account.id, 'name': f'Transfer from {exchange_gain_account.display_name}',
             'balance': -100.0, 'amount_currency': 0.0, 'currency_id': self.foreign_currency.id},
            {'account_id': exchange_gain_account.id, 'name': f'Transfer to {self.receivable_account.display_name}',
             'balance': 100.0, 'amount_currency': 0.0, 'currency_id': self.foreign_currency.id},
        ]
        expected_values = [
            {'account_id': self.receivable_account.id, 'name': 'Write-Off Test Label',
             'balance': -50.0, 'amount_currency': -50.0, 'currency_id': self.company_currency.id},
            {'account_id': self.write_off_account.id, 'name': 'Write-Off Test Label',
             'balance': 50.0, 'amount_currency': 50.0, 'currency_id': self.company_currency.id},
        ]
        self.assertWizardReconcileValues(line_1 + line_2, wizard_input_values, expected_values, expected_transfer_values=expected_transfer_values)

    def test_write_off_on_same_account(self):
        """ When creating a write-off in the same account than the one used by the lines to reconcile,
        the lines and the write-off should be fully reconciled.
        """
        line_1 = self.create_line_for_reconciliation(1000.0, 1000.0, self.company_currency, '2016-01-01')
        line_2 = self.create_line_for_reconciliation(2000.0, 2000.0, self.company_currency, '2016-01-01')
        wizard_input_values = {
            'journal_id': self.misc_journal.id,
            'account_id': self.receivable_account.id,
            'label': 'Write-Off Test Label',
            'allow_partials': False,
            'date': self.test_date,
        }
        write_off_expected_values = [
            {'account_id': self.receivable_account.id, 'name': 'Write-Off Test Label', 'balance': -3000.0},
            {'account_id': self.receivable_account.id, 'name': 'Write-Off Test Label', 'balance': 3000.0},
        ]
        self.assertWizardReconcileValues(line_1 + line_2, wizard_input_values, write_off_expected_values)

    def test_reconcile_exchange_diff_foreign_currency_full(self):
        """ When reconciling exchange_diff with amount_residual_currency = 0 we need to reconcile in company_currency.
        """
        exchange_gain_account = self.company_data['company'].income_currency_exchange_account_id
        exchange_gain_account.reconcile = True
        line_1 = self.create_line_for_reconciliation(100.0, 0.0, self.foreign_currency, '2016-01-01')
        line_2 = self.create_line_for_reconciliation(-100.0, 0.0, self.foreign_currency, '2016-01-01', account_1=exchange_gain_account)
        lines = line_1 + line_2
        lines.action_reconcile()
        self.assertTrue(lines.full_reconcile_id)
        self.assertRecordValues(
            lines,
            [{'amount_residual': 0.0, 'amount_residual_currency': 0.0, 'reconciled': True}] * len(lines),
        )

    def test_write_off_kpmg_case(self):
        """ Test that write-off does a full reconcile with 2 foreign currencies using a custom exchange rate. """
        new_date = fields.Date.from_string('2017-02-01')
        line_1 = self.create_line_for_reconciliation(1000.0, 1500.0, self.foreign_currency, '2016-01-01')
        line_2 = self.create_line_for_reconciliation(-900.0, -5400.0, self.foreign_currency_2, '2016-01-01')
        wizard_input_values = {
            'journal_id': self.misc_journal.id,
            'account_id': self.write_off_account.id,
            'label': 'Write-Off Test Label',
            'allow_partials': False,
            'date': new_date,
        }
        self.assertWizardReconcileValues(line_1 + line_2, wizard_input_values, [
            {
                'account_id': self.receivable_account.id,
                'balance': -100.0,
                'amount_currency': -150.0,
                'currency_id': self.foreign_currency.id,
            },
            {
                'account_id': self.write_off_account.id,
                'balance': 100.0,
                'amount_currency': 150.0,
                'currency_id': self.foreign_currency.id,
            },
        ])

    def test_write_off_multi_curr_multi_residuals_force_partials(self):
        """ Test that we raise an error when trying to reconcile lines with multiple residuals.
         Here debit1 will be reconciled with credit1 first as they have the same currency.
         Then residual of debit1 will try to reconcile with debit2 which is impossible
         => 2 residuals both in foreign currency, we don't know in which currency we should make the write-off
         => We should only allow partial reconciliation. """
        debit_1 = self.create_line_for_reconciliation(2000.0, 12000.0, self.foreign_currency_2, '2016-01-01')
        credit_1 = self.create_line_for_reconciliation(-1000.0, -6000.0, self.foreign_currency_2, '2016-01-01')
        debit_2 = self.create_line_for_reconciliation(2000.0, 3000.0, self.foreign_currency, '2016-01-01')
        wizard = self.env['account.reconcile.wizard'].with_context(
            active_model='account.move.line',
            active_ids=(debit_1 + debit_2 + credit_1).ids,
        ).new()
        self.assertRecordValues(wizard, [{'force_partials': True, 'allow_partials': True}])

    def test_write_off_multi_curr_multi_residuals_exch_diff_force_partials(self):
        debit_1 = self.create_line_for_reconciliation(2000.0, 0.0, self.foreign_currency_2, '2016-01-01')
        credit_1 = self.create_line_for_reconciliation(-1000.0, 0.0, self.foreign_currency_2, '2016-01-01')
        debit_2 = self.create_line_for_reconciliation(2000.0, 0.0, self.foreign_currency, '2016-01-01')
        wizard = self.env['account.reconcile.wizard'].with_context(
            active_model='account.move.line',
            active_ids=(debit_1 + debit_2 + credit_1).ids,
        ).new()
        self.assertRecordValues(wizard, [{'force_partials': True, 'allow_partials': True}])

    def test_reconcile_with_partner_change(self):
        partner_1 = self.env['res.partner'].create({'name': 'Test Partner 1'})
        partner_2 = self.env['res.partner'].create({'name': 'Test Partner 2'})
        line_1 = self.create_line_for_reconciliation(-1000.0, -1000.0, self.company_currency, '2016-01-01', partner=partner_1)
        line_2 = self.create_line_for_reconciliation(2000.0, 2000.0, self.company_currency, '2016-01-01')
        wizard_input_values = {
            'journal_id': self.misc_journal.id,
            'account_id': self.receivable_account.id,
            'to_partner_id': partner_2.id,
            'label': 'Write-Off Test Label',
            'allow_partials': False,
            'date': self.test_date,
            'tax_id': self.tax_sale_a.id,
        }
        write_off_expected_values = [
            {'account_id': self.receivable_account.id, 'name': 'Write-Off Test Label', 'balance': -1000.0, 'partner_id': partner_1.id},
            {'account_id': self.company_data['default_account_tax_sale'].id, 'name': '15%', 'balance': 130.43, 'partner_id': partner_2.id},
            {'account_id': self.receivable_account.id, 'name': 'Write-Off Test Label', 'balance': 869.57, 'partner_id': partner_2.id},
        ]
        self.assertWizardReconcileValues(line_1 + line_2, wizard_input_values, write_off_expected_values)

    def test_reconcile_with_partner_change_and_transfer(self):
        partner_1 = self.env['res.partner'].create({'name': 'Test Partner 1'})
        partner_2 = self.env['res.partner'].create({'name': 'Test Partner 2'})
        line_1 = self.create_line_for_reconciliation(-1000.0, -1000.0, self.company_currency, '2016-01-01', account_1=self.payable_account)
        line_2 = self.create_line_for_reconciliation(2000.0, 2000.0, self.company_currency, '2016-01-01', partner=partner_1)
        wizard_input_values = {
            'journal_id': self.misc_journal.id,
            'account_id': self.receivable_account.id,
            'to_partner_id': partner_2.id,
            'label': 'Write-Off Test Label',
            'allow_partials': False,
            'date': self.test_date,
        }
        expected_transfer_values = [
            {'account_id': self.receivable_account.id, 'name': f'Transfer from {self.payable_account.display_name}',
             'balance': -1000.0, 'amount_currency': -1000.0, 'currency_id': self.company_currency.id},
            {'account_id': self.payable_account.id, 'name': f'Transfer to {self.receivable_account.display_name}',
             'balance': 1000.0, 'amount_currency': 1000.0, 'currency_id': self.company_currency.id},
        ]
        write_off_expected_values = [
            {'account_id': self.receivable_account.id, 'name': 'Write-Off Test Label', 'balance': -1000.0, 'partner_id': partner_1.id},
            {'account_id': self.receivable_account.id, 'name': 'Write-Off Test Label', 'balance': 1000.0, 'partner_id': partner_2.id},
        ]
        self.assertWizardReconcileValues(line_1 + line_2, wizard_input_values, write_off_expected_values, expected_transfer_values)

    def test_reconcile_edit_mode_partial_foreign_curr(self):
        line_1 = self.create_line_for_reconciliation(100.0, 300.0, self.foreign_currency, '2016-01-01')
        wizard_input_values = {
            'account_id': self.write_off_account.id,
            'label': 'Write-Off Test Label',
            'date': self.test_date,
            'edit_mode_amount_currency': 30.0,
        }
        expected_values = [
            {'account_id': self.receivable_account.id, 'name': 'Write-Off Test Label',
             'balance': -10.0, 'amount_currency': -30.0, 'currency_id': self.foreign_currency.id},
            {'account_id': self.write_off_account.id, 'name': 'Write-Off Test Label',
             'balance': 10.0, 'amount_currency': 30.0, 'currency_id': self.foreign_currency.id},
        ]
        self.assertWizardReconcileValues(line_1, wizard_input_values, expected_values)

    def test_reconcile_edit_mode_partial_company_curr(self):
        line_1 = self.create_line_for_reconciliation(300.0, 300.0, self.company_currency, '2016-01-01')
        wizard_input_values = {
            'account_id': self.write_off_account.id,
            'label': 'Write-Off Test Label',
            'date': self.test_date,
            'edit_mode_amount_currency': 100.0,
        }
        expected_values = [
            {'account_id': self.receivable_account.id, 'name': 'Write-Off Test Label',
             'balance': -100.0, 'amount_currency': -100.0, 'currency_id': self.company_currency.id},
            {'account_id': self.write_off_account.id, 'name': 'Write-Off Test Label',
             'balance': 100.0, 'amount_currency': 100.0, 'currency_id': self.company_currency.id},
        ]
        self.assertWizardReconcileValues(line_1, wizard_input_values, expected_values)

    def test_reconcile_edit_mode_partial_wrong_amount_raises(self):
        line_1 = self.create_line_for_reconciliation(300.0, 300.0, self.company_currency, '2016-01-01')
        wizard_input_values = {
            'account_id': self.write_off_account.id,
        }
        wizard = self.env['account.reconcile.wizard'].with_context(
            active_model='account.move.line',
            active_ids=line_1.ids,
        ).create(wizard_input_values)
        with self.assertRaisesRegex(UserError, 'The amount of the write-off'):
            wizard.edit_mode_amount_currency = -100.0

    def test_reconcile_edit_mode_full_reconcile(self):
        line_1 = self.create_line_for_reconciliation(300.0, 300.0, self.company_currency, '2016-01-01')
        wizard_input_values = {
            'account_id': self.write_off_account.id,
            'label': 'Write-Off Test Label',
            'edit_mode_amount_currency': 300.0,
        }
        expected_values = [
            {'account_id': self.receivable_account.id, 'name': 'Write-Off Test Label',
             'balance': -300.0, 'amount_currency': -300.0, 'currency_id': self.company_currency.id},
            {'account_id': self.write_off_account.id, 'name': 'Write-Off Test Label',
             'balance': 300.0, 'amount_currency': 300.0, 'currency_id': self.company_currency.id},
        ]
        self.assertWizardReconcileValues(line_1, wizard_input_values, expected_values)

    def test_reconcile_same_currency_same_side_not_recpay(self):
        """
        Test the reconciliation with two lines on the same side (debit/credit), same currency and not on a receivable/payable account
        """
        current_assets_account = self.company_data['default_account_assets'].copy({'name': 'Current Assets', 'account_type': 'asset_current', 'reconcile': True})
        line_1 = self.create_line_for_reconciliation(200, 200, self.company_currency, '2016-01-01', current_assets_account)
        line_2 = self.create_line_for_reconciliation(200, 200, self.company_currency, '2016-01-01', current_assets_account)

        # Test the opening of the wizard without input values
        wizard = self.env['account.reconcile.wizard'].with_context(
            active_model='account.move.line',
            active_ids=(line_1 + line_2).ids,
        ).new()

        self.assertRecordValues(wizard, [{'is_write_off_required': True, 'amount': 400, 'amount_currency': 400}])

        wizard_input_values = {
            'journal_id': self.misc_journal.id,
            'account_id': self.write_off_account.id,
            'label': 'Write-Off Test Label',
            'allow_partials': False,
            'date': self.test_date,
        }
        expected_values = [
            {'account_id': current_assets_account.id, 'name': 'Write-Off Test Label',
             'balance': -400.0, 'amount_currency': -400.0, 'currency_id': self.company_currency.id},
            {'account_id': self.write_off_account.id, 'name': 'Write-Off Test Label',
             'balance': 400.0, 'amount_currency': 400.0, 'currency_id': self.company_currency.id},
        ]
        self.assertWizardReconcileValues(line_1 + line_2, wizard_input_values, expected_values)

    def test_reconcile_foreign_currency_same_side_not_recpay(self):
        """
        Test the reconciliation with two lines on the same side (debit/credit), one foreign currency and not on a receivable/payable account
        """
        current_assets_account = self.company_data['default_account_assets'].copy({'name': 'Current Assets', 'account_type': 'asset_current', 'reconcile': True})
        line_1 = self.create_line_for_reconciliation(200, 300, self.foreign_currency, '2016-01-01', current_assets_account)
        line_2 = self.create_line_for_reconciliation(200, 200, self.company_currency, '2016-01-01', current_assets_account)

        # Test the opening of the wizard without input values
        wizard = self.env['account.reconcile.wizard'].with_context(
            active_model='account.move.line',
            active_ids=(line_1 + line_2).ids,
        ).new()

        self.assertRecordValues(wizard, [{'is_write_off_required': True, 'amount': 400, 'amount_currency': 400}])

        wizard_input_values = {
            'journal_id': self.misc_journal.id,
            'account_id': self.write_off_account.id,
            'label': 'Write-Off Test Label',
            'allow_partials': False,
            'date': self.test_date,
        }
        expected_values = [
            {'account_id': current_assets_account.id, 'name': 'Write-Off Test Label',
             'balance': -400.0, 'amount_currency': -400.0, 'currency_id': self.company_currency.id},
            {'account_id': self.write_off_account.id, 'name': 'Write-Off Test Label',
             'balance': 400.0, 'amount_currency': 400.0, 'currency_id': self.company_currency.id},
        ]
        self.assertWizardReconcileValues(line_1 + line_2, wizard_input_values, expected_values)

    def test_reconcile_same_side_exch_diff(self):
        """
        Test the reconciliation with two lines on the same side (debit/credit), one exchange diff in foreign currency,
        one regular aml in company currency
        """
        exchange_gain_account = self.company_data['company'].income_currency_exchange_account_id
        exchange_gain_account.reconcile = True
        line_1 = self.create_line_for_reconciliation(150.0, 150.0, self.company_currency, '2016-01-01')
        line_2 = self.create_line_for_reconciliation(100.0, 0.0, self.foreign_currency, '2016-01-01', account_1=exchange_gain_account)
        wizard_input_values = {
            'journal_id': self.misc_journal.id,
            'account_id': self.write_off_account.id,
            'label': 'Write-Off Test Label',
            'allow_partials': False,
            'date': self.test_date,
        }
        # Note the transfer will always be in the currency of the line transferred
        expected_transfer_values = [
            {'account_id': exchange_gain_account.id, 'name': f'Transfer to {self.receivable_account.display_name}',
             'balance': -100.0, 'amount_currency': 0.0, 'currency_id': self.foreign_currency.id},
            {'account_id': self.receivable_account.id, 'name': f'Transfer from {exchange_gain_account.display_name}',
             'balance': 100.0, 'amount_currency': 0.0, 'currency_id': self.foreign_currency.id},
        ]
        expected_values = [
            {'account_id': self.receivable_account.id, 'name': 'Write-Off Test Label',
             'balance': -250.0, 'amount_currency': -250.0, 'currency_id': self.company_currency.id},
            {'account_id': self.write_off_account.id, 'name': 'Write-Off Test Label',
             'balance': 250.0, 'amount_currency': 250.0, 'currency_id': self.company_currency.id},
        ]
        self.assertWizardReconcileValues(line_1 + line_2, wizard_input_values, expected_values, expected_transfer_values=expected_transfer_values)

    def test_reconcile_transfer_with_different_partners(self):
        """ When balance is 0, and we need a transfer, we do the transfer+reconcile silently. """
        partner_a = self.env['res.partner'].create({'name': 'Test Partner A'})
        partner_b = self.env['res.partner'].create({'name': 'Test Partner B'})
        partner_c = self.env['res.partner'].create({'name': 'Test Partner C'})
        # when reconciling journal items on 2 different accounts from 2 different partners that balance themselves,
        # all journal items should be fully reconciled together
        line_a1 = self.create_line_for_reconciliation(1000.0, 1000.0, self.company_currency, '2016-01-01', account_1=self.receivable_account, partner=partner_a)
        line_b1 = self.create_line_for_reconciliation(-1000.0, -1000.0, self.company_currency, '2016-01-01', account_1=self.payable_account, partner=partner_b)
        lines = line_a1 + line_b1
        lines.action_reconcile()
        transfer_lines = lines.full_reconcile_id.reconciled_line_ids.filtered(lambda line: line.id not in lines.ids)
        self.assertRecordValues(transfer_lines, [
            {'balance': -1000.0, 'account_id': self.receivable_account.id, 'partner_id': partner_a.id},
            {'balance': 1000.0, 'account_id': self.payable_account.id, 'partner_id': partner_b.id},
        ])
        # even if the journal items on one of the accounts are for several different partners,
        # the journal items should be fully reconciled together
        line_a2 = self.create_line_for_reconciliation(1000.0, 1000.0, self.company_currency, '2016-01-01', account_1=self.receivable_account, partner=partner_a)
        line_b2 = self.create_line_for_reconciliation(-600.0, -600.0, self.company_currency, '2016-01-01', account_1=self.payable_account, partner=partner_b)
        line_c2 = self.create_line_for_reconciliation(-400.0, -400.0, self.company_currency, '2016-01-01', account_1=self.payable_account, partner=partner_c)
        lines = line_a2 + line_b2 + line_c2
        lines.action_reconcile()
        transfer_lines = lines.full_reconcile_id.reconciled_line_ids.filtered(lambda line: line.id not in lines.ids)
        self.assertRecordValues(transfer_lines, [
            {'balance': -1000.0, 'account_id': self.receivable_account.id, 'partner_id': partner_a.id},
            {'balance': 600.0, 'account_id': self.payable_account.id, 'partner_id': partner_b.id},
            {'balance': 400.0, 'account_id': self.payable_account.id, 'partner_id': partner_c.id},
        ])
