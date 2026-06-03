from odoo import Command
from odoo.exceptions import RedirectWarning, ValidationError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nCNBalanceDeduction(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('cn')
    def setUpClass(cls):
        super().setUpClass()

        cls.invoice = cls._create_invoice(
            move_type='out_invoice',
            invoice_date='2026-08-01',
            partner_id=cls.partner_a.id,
            invoice_line_ids=[
                cls._prepare_invoice_line(
                    price_unit=1000,
                    tax_ids=cls.tax_sale_a,
                ),
            ],
        )

        cls.expense_account = cls.company_data['default_account_expense']
        cls.second_expense_account = cls.env['account.account'].create({
            'name': 'Second CN Expense Account',
            'code': 'CNEXP002',
            'account_type': 'expense',
        })
        cls.company.l10n_cn_vat_differential_taxation = True

    def _add_balance_deductions(self, invoice_line, deductions):
        invoice_line.l10n_cn_balance_deduction_ids = [
            Command.create(deduction_vals)
            for deduction_vals in deductions
        ]

    def test_net_amount_fapiao_posting_requires_deduction_and_creates_offset_entry(self):
        """Ensure net amount Fapiao posting requires balance deductions and creates a valid VAT offset entry."""
        self.invoice.l10n_cn_differential_taxation_method = '02'

        with self.assertRaises(ValidationError):
            self.invoice.action_post()

        invoice_line = self.invoice.invoice_line_ids[0]

        self._add_balance_deductions(
            invoice_line,
            [{
                'voucher_type': '10',
                'voucher_total': 100.0,
                'deduct_amount': 100.0,
                'e_fapiao_number': 'EF001',
                'issue_date': '2026-08-01',
                'expense_account_id': self.expense_account.id,
            }],
        )

        self.invoice.action_post()

        self.assertRecordValues(
            self.invoice.l10n_cn_output_vat_offset_move_ids.line_ids.sorted(),
            [
                {
                    'account_id': invoice_line.l10n_cn_output_vat_offset_account_id.id,
                    'balance': 11.5,  # (100 / 1.13) * 0.13
                },
                {
                    'account_id': self.expense_account.id,
                    'balance': -11.5,
                },
            ],
        )

        offset_moves = self.invoice.l10n_cn_output_vat_offset_move_ids

        # Directly resetting the offset move to draft should not be allowed.
        with self.assertRaises(RedirectWarning):
            offset_moves.button_draft()

        # Directly reversing the offset move should not be allowed.
        with self.assertRaises(RedirectWarning):
            self.env['account.move.reversal'].with_context(
                active_model='account.move',
                active_ids=offset_moves.ids,
                active_id=offset_moves.id,
            ).create({})

    def test_net_amount_fapiao_creates_offset_entry_for_multiple_deductions_and_invoice_lines(self):
        """Ensure multiple deductions across multiple invoice lines create one offset entry with correct balances."""
        self.invoice.invoice_line_ids = [
            self._prepare_invoice_line(
                price_unit=500,
                tax_ids=self.tax_sale_a,
            ),
        ]
        first_invoice_line, second_invoice_line = self.invoice.invoice_line_ids
        self._add_balance_deductions(
            first_invoice_line,
            [
                {
                    'voucher_type': '10',
                    'voucher_total': 100.0,
                    'deduct_amount': 100.0,
                    'e_fapiao_number': 'EF001',
                    'issue_date': '2026-08-01',
                    'expense_account_id': self.expense_account.id,
                },
                {
                    'voucher_type': '10',
                    'voucher_total': 200.0,
                    'deduct_amount': 200.0,
                    'e_fapiao_number': 'EF002',
                    'issue_date': '2026-08-01',
                    'expense_account_id': self.second_expense_account.id,
                },
            ],
        )
        self._add_balance_deductions(
            second_invoice_line,
            [{
                'voucher_type': '10',
                'voucher_total': 100.0,
                'deduct_amount': 100.0,
                'e_fapiao_number': 'EF003',
                'issue_date': '2026-08-01',
                'expense_account_id': self.expense_account.id,
            }],
        )
        self.invoice.l10n_cn_differential_taxation_method = '02'
        self.invoice.action_post()
        self.assertRecordValues(
            self.invoice.l10n_cn_output_vat_offset_move_ids.line_ids.sorted(),
            [
                {
                    'account_id': first_invoice_line.l10n_cn_output_vat_offset_account_id.id,
                    'balance': 34.51,  # 11.5 + 23.01
                },
                {
                    'account_id': self.expense_account.id,
                    'balance': -11.5,  # (100 / 1.13) * 0.13
                },
                {
                    'account_id': self.second_expense_account.id,
                    'balance': -23.01,  # (200 / 1.13) * 0.13
                },
                {
                    'account_id': second_invoice_line.l10n_cn_output_vat_offset_account_id.id,
                    'balance': 11.5,
                },
                {
                    'account_id': self.expense_account.id,
                    'balance': -11.5,  # (100 / 1.13) * 0.13
                },
            ],
        )

    def test_net_amount_fapiao_requires_deductions_for_all_applicable_lines(self):
        """Ensure every applicable invoice line must have deductions for net amount Fapiao."""
        self.invoice.invoice_line_ids = [
            self._prepare_invoice_line(
                price_unit=500,
                tax_ids=self.tax_sale_a,
            ),
        ]

        first_invoice_line = self.invoice.invoice_line_ids[0]

        self._add_balance_deductions(
            first_invoice_line,
            [{
                'voucher_type': '10',
                'voucher_total': 100.0,
                'deduct_amount': 100.0,
                'e_fapiao_number': 'EF001',
                'issue_date': '2026-08-01',
                'expense_account_id': self.expense_account.id,
            }],
        )

        self.invoice.l10n_cn_differential_taxation_method = '02'

        with self.assertRaises(ValidationError):
            self.invoice.action_post()

    def test_full_amount_fapiao_creates_offset_entries_for_multiple_invoice_lines(self):
        """Ensure full amount Fapiao creates one offset entry per applicable invoice line."""
        self.invoice.invoice_line_ids = [
            self._prepare_invoice_line(
                price_unit=500,
                tax_ids=self.tax_sale_a,
            ),
        ]

        first_invoice_line, second_invoice_line = self.invoice.invoice_line_ids

        self._add_balance_deductions(
            first_invoice_line,
            [{
                'voucher_type': '10',
                'voucher_total': 100.0,
                'deduct_amount': 100.0,
                'e_fapiao_number': 'EF001',
                'issue_date': '2026-08-01',
                'expense_account_id': self.expense_account.id,
            }],
        )

        self._add_balance_deductions(
            second_invoice_line,
            [{
                'voucher_type': '10',
                'voucher_total': 200.0,
                'deduct_amount': 200.0,
                'e_fapiao_number': 'EF002',
                'issue_date': '2026-08-01',
                'expense_account_id': self.expense_account.id,
            }],
        )

        self.invoice.l10n_cn_differential_taxation_method = '01'
        self.invoice.action_post()

        offset_moves = self.invoice.l10n_cn_output_vat_offset_move_ids
        self.assertEqual(len(offset_moves), 2)

        self.assertRecordValues(
            offset_moves.line_ids.sorted(),
            [
                {
                    'account_id': second_invoice_line.l10n_cn_output_vat_offset_account_id.id,
                    'balance': 23.01,  # (200 / 1.13) * 0.13
                },
                {
                    'account_id': self.expense_account.id,
                    'balance': -23.01,
                },
                {
                    'account_id': first_invoice_line.l10n_cn_output_vat_offset_account_id.id,
                    'balance': 11.5,  # (100 / 1.13) * 0.13
                },
                {
                    'account_id': self.expense_account.id,
                    'balance': -11.5,
                },
            ],
        )

        # Reset the first invoice line and create its reversal entry.
        first_invoice_line.action_reset_balance_deduction_to_draft()

        self.assertFalse(first_invoice_line.l10n_cn_output_vat_offset_move_id)

        reversed_offset_move = self.invoice.l10n_cn_output_vat_offset_move_ids - offset_moves

        self.assertEqual(len(reversed_offset_move), 1)
        self.assertEqual(
            reversed_offset_move.l10n_cn_output_vat_offset_origin_id,
            self.invoice,
        )

        # Update the deduction amount and recreate the offset entry.
        first_invoice_line.l10n_cn_balance_deduction_ids.deduct_amount = 50.0
        first_invoice_line.action_save_l10n_cn_balance_deduction()

        new_offset_move = first_invoice_line.l10n_cn_output_vat_offset_move_id

        self.assertIn(new_offset_move, self.invoice.l10n_cn_output_vat_offset_move_ids)

        self.assertRecordValues(
            new_offset_move.line_ids.sorted(),
            [
                {
                    'account_id': first_invoice_line.l10n_cn_output_vat_offset_account_id.id,
                    'balance': 5.75,  # (50 / 1.13) * 0.13
                },
                {
                    'account_id': self.expense_account.id,
                    'balance': -5.75,
                },
            ],
        )

    def test_full_amount_fapiao_creates_offset_entry_after_adding_deduction(self):
        """Ensure adding a deduction after posting creates an offset entry on save."""
        self.invoice.l10n_cn_differential_taxation_method = '01'
        self.invoice.action_post()

        invoice_line = self.invoice.invoice_line_ids[0]

        self.assertFalse(invoice_line.l10n_cn_output_vat_offset_move_id)
        self.assertFalse(self.invoice.l10n_cn_output_vat_offset_move_ids)

        self._add_balance_deductions(
            invoice_line,
            [{
                'voucher_type': '10',
                'voucher_total': 100.0,
                'deduct_amount': 100.0,
                'e_fapiao_number': 'EF001',
                'issue_date': '2026-08-01',
                'expense_account_id': self.expense_account.id,
            }],
        )

        invoice_line.action_save_l10n_cn_balance_deduction()

        offset_move = invoice_line.l10n_cn_output_vat_offset_move_id

        self.assertTrue(offset_move)
        self.assertIn(offset_move, self.invoice.l10n_cn_output_vat_offset_move_ids)

        self.assertRecordValues(
            offset_move.line_ids.sorted(),
            [
                {
                    'account_id': invoice_line.l10n_cn_output_vat_offset_account_id.id,
                    'balance': 11.5,  # (100 / 1.13) * 0.13
                },
                {
                    'account_id': self.expense_account.id,
                    'balance': -11.5,
                },
            ],
        )

    def test_full_amount_fapiao_button_draft_reverses_active_offset_entries(self):
        """Ensure resetting the invoice reverses all active offset entries and skips already reversed entries."""
        self.invoice.invoice_line_ids = [
            self._prepare_invoice_line(
                price_unit=500,
                tax_ids=self.tax_sale_a,
            ),
        ]

        first_invoice_line, second_invoice_line = self.invoice.invoice_line_ids

        self._add_balance_deductions(
            first_invoice_line,
            [{
                'voucher_type': '10',
                'voucher_total': 100.0,
                'deduct_amount': 100.0,
                'e_fapiao_number': 'EF001',
                'issue_date': '2026-08-01',
                'expense_account_id': self.expense_account.id,
            }],
        )
        self._add_balance_deductions(
            second_invoice_line,
            [{
                'voucher_type': '10',
                'voucher_total': 200.0,
                'deduct_amount': 200.0,
                'e_fapiao_number': 'EF002',
                'issue_date': '2026-08-01',
                'expense_account_id': self.expense_account.id,
            }],
        )

        self.invoice.l10n_cn_differential_taxation_method = '01'
        self.invoice.action_post()

        offset_moves = self.invoice.l10n_cn_output_vat_offset_move_ids
        self.assertEqual(len(offset_moves), 2)

        first_offset_move = first_invoice_line.l10n_cn_output_vat_offset_move_id
        second_offset_move = second_invoice_line.l10n_cn_output_vat_offset_move_id

        self.assertEqual(set(offset_moves), {first_offset_move, second_offset_move})

        first_invoice_line.action_reset_balance_deduction_to_draft()

        first_reversal = (
            self.invoice.l10n_cn_output_vat_offset_move_ids
            - offset_moves
        )

        self.assertEqual(len(first_reversal), 1)
        self.assertEqual(first_reversal.reversed_entry_id, first_offset_move)
        self.assertEqual(
            first_reversal.l10n_cn_output_vat_offset_origin_id,
            self.invoice,
        )

        # Reset the invoice to draft. The already reversed first offset must be
        # skipped, while the still-active second offset must be reversed.
        self.invoice.button_draft()

        all_offset_moves = self.invoice.l10n_cn_output_vat_offset_move_ids

        self.assertEqual(len(all_offset_moves), 4)

        self.assertEqual(
            set(offset_moves.mapped('l10n_cn_output_vat_offset_origin_id')),
            {self.invoice},
        )

        first_reversals = all_offset_moves.filtered(
            lambda move: move.reversed_entry_id == first_offset_move,
        )
        self.assertEqual(len(first_reversals), 1)
        self.assertEqual(first_reversals, first_reversal)

        second_reversals = all_offset_moves.filtered(
            lambda move: move.reversed_entry_id == second_offset_move,
        )
        self.assertEqual(len(second_reversals), 1)

        self.assertEqual(
            second_reversals.l10n_cn_output_vat_offset_origin_id,
            self.invoice,
        )

        self.assertEqual(
            len(all_offset_moves.filtered(
                lambda move: move.reversed_entry_id == first_reversal,
            )),
            0,
        )

        self.assertFalse(first_invoice_line.l10n_cn_output_vat_offset_move_id)
        self.assertFalse(second_invoice_line.l10n_cn_output_vat_offset_move_id)

    def test_net_amount_fapiao_credit_note_with_multiple_invoice_lines(self):
        """Ensure a credit note copies all invoice lines and deductions and creates one offset entry."""
        self.invoice.invoice_line_ids = [
            self._prepare_invoice_line(
                price_unit=500,
                tax_ids=self.tax_sale_a,
            ),
        ]

        first_invoice_line, second_invoice_line = self.invoice.invoice_line_ids

        self._add_balance_deductions(
            first_invoice_line,
            [{
                'voucher_type': '10',
                'voucher_total': 100.0,
                'deduct_amount': 100.0,
                'e_fapiao_number': 'EF001',
                'issue_date': '2026-08-01',
                'expense_account_id': self.expense_account.id,
            }],
        )
        self._add_balance_deductions(
            second_invoice_line,
            [{
                'voucher_type': '10',
                'voucher_total': 200.0,
                'deduct_amount': 200.0,
                'e_fapiao_number': 'EF002',
                'issue_date': '2026-08-01',
                'expense_account_id': self.second_expense_account.id,
            }],
        )

        self.invoice.l10n_cn_differential_taxation_method = '02'
        self.invoice.action_post()

        credit_note = self.invoice._reverse_moves(
            default_values_list=[{'move_type': 'out_refund'}],
            cancel=False,
        )[0]

        self.assertEqual(len(credit_note.invoice_line_ids), 2)

        first_credit_line, second_credit_line = credit_note.invoice_line_ids

        self.assertRecordValues(
            credit_note.invoice_line_ids.l10n_cn_balance_deduction_ids.sorted(),
            [
                {
                    'deduct_amount': 100.0,
                    'expense_account_id': self.expense_account.id,
                },
                {
                    'deduct_amount': 200.0,
                    'expense_account_id': self.second_expense_account.id,
                },
            ],
        )

        credit_note.action_post()

        offset_moves = credit_note.l10n_cn_output_vat_offset_move_ids

        self.assertRecordValues(
            offset_moves.line_ids.sorted(),
            [
                {
                    'account_id': first_credit_line.l10n_cn_output_vat_offset_account_id.id,
                    'balance': -11.5,  # (100 / 1.13) * 0.13
                },
                {
                    'account_id': self.expense_account.id,
                    'balance': 11.5,
                },
                {
                    'account_id': second_credit_line.l10n_cn_output_vat_offset_account_id.id,
                    'balance': -23.01,  # (200 / 1.13) * 0.13
                },
                {
                    'account_id': self.second_expense_account.id,
                    'balance': 23.01,
                },
            ],
        )
