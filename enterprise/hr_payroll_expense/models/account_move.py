# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.exceptions import AccessError


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _post(self, soft=True):
        # EXTENDS account
        # In the case where an expense is reimbursed through an employee's payslip, we need to reconcile the move generated
        # for the expense and the one generated for the payslip, so the expense can be set to 'paid'
        # and only one payment shall be made, the payslip one. If the moves have been altered, the automatic reconciliation may not be done,
        # it will be done manually by an accountant. We will keep the temporary matching data to simplify that case.
        lines_to_reconcile = self.env['account.move.line']
        if not self.env.context.get('skip_reconcile_expense_with_payslip'):
            self = self.with_context(skip_reconcile_expense_with_payslip=True)  # noqa: PLW0642 Avoid entering here recursively
            lines_to_reconcile = self._hr_payroll_expense_prepare_move_lines_to_reconcile()

        res = super()._post(soft=soft)  # Posting will automatically reconcile same-account-same-matching lines

        lines_to_reconcile = lines_to_reconcile.filtered(lambda line: not line.reconciled)
        if lines_to_reconcile:
            # Tries to reconcile move lines automatically (to mark the expense as paid)
            wizard = self.env['account.reconcile.wizard'].with_context(
                active_model='account.move.line',
                active_ids=lines_to_reconcile.ids,
            ).new({})
            if not (wizard.is_write_off_required or wizard.force_partials):  # Only reconcile if there are no issue that requires user-input
                wizard.reconcile()
        return res

    def unlink(self):
        # EXTENDS account
        moves_to_unlink = self.sudo().payslip_ids.expense_sheet_ids.account_move_ids.ids
        if moves_to_unlink:
            self.browse(moves_to_unlink)._unlink_or_reverse()
        return super().unlink()

    def _hr_payroll_expense_prepare_move_lines_to_reconcile(self):
        """
            (Create if None &) Post the expense's move and prepare it to be reconciled with the payslip move,
            as the expense is reimbursed to the employee through the payslip.
            This ensures the payment state of the expense, its report, and move are set to 'paid'.
        """
        if not self.env.is_superuser() and not self.env.user.has_group('account.group_account_invoice'):
            raise AccessError(_("You don't have the access rights to post an invoice."))

        payslips_sudo = self.sudo().payslip_ids
        if not payslips_sudo.expense_sheet_ids:
            return self.env['account.move.line']  # No payslip or expenses, no reason to continue

        # Create missing expense sheets moves (if any)
        sheets_without_moves = payslips_sudo.expense_sheet_ids.filtered(lambda sheet: not sheet.account_move_ids)
        if sheets_without_moves:
            sheets_without_moves._do_create_moves()

        # Prepare the reconciliation by grouping expense sheet moves per payslip move
        payslip_move_to_expense_move_map = {}

        # Handles the case where an account move linked to an expense is already paid, ignoring the fact that it was flagged to be paid here
        # (They will get paid twice, but it's the user's responsibility)
        valid_expense_sheets_sudo = payslips_sudo.expense_sheet_ids.filtered(
            lambda sheet: sheet.payment_state == 'not_paid' and sheet.account_move_ids
        )
        for payslip_sudo, expense_sheets_sudo in valid_expense_sheets_sudo.grouped('payslip_id').items():
            payslip_move_to_expense_move_map.setdefault(payslip_sudo.move_id, self.env['account.move'].sudo())
            payslip_move_to_expense_move_map[payslip_sudo.move_id] |= expense_sheets_sudo.sorted().account_move_ids

        # Prepare and collect the reconciliation lines
        lines_to_reconcile_sudo = self.env['account.move.line']
        rule_account_id_per_struct_id = payslips_sudo.struct_id._get_expense_rule_account_id_map(payslips_sudo.company_id)
        for idx, (payslip_move_sudo, expense_moves_sudo) in enumerate(payslip_move_to_expense_move_map.items()):
            # Get the payslip move lines generated for the expenses
            payslip_account_id = rule_account_id_per_struct_id[payslip_move_sudo.payslip_ids.struct_id.id]  # Only one structure per move
            lines_to_match_sudo = payslip_move_sudo.line_ids.filtered(
                lambda aml: aml.account_id.id == payslip_account_id and aml.display_type != 'payment_term'
            )

            # Get the corresponding payable lines for the expenses
            lines_to_match_sudo |= expense_moves_sudo.line_ids.filtered(lambda aml: aml.account_id.account_type == 'liability_payable')

            # Use the matching number system to simplify reconciliation, the number itself is just made to be unique
            lines_to_match_sudo.matching_number = f'{idx:0>10}-{payslip_move_sudo.id}-{min(expense_moves_sudo.ids)}'
            lines_to_reconcile_sudo |= lines_to_match_sudo

        # Post all expense sheet moves that aren't posted already
        expense_moves_to_post_sudo = payslips_sudo.expense_sheet_ids.account_move_ids.filtered(lambda move: move.state == 'draft')
        if expense_moves_to_post_sudo:
            expense_moves_to_post_sudo._post(soft=False)

        # If we have more than 2 accounts, we will not be able to reconcile
        if len(lines_to_reconcile_sudo.account_id) > 2:
            return self.env['account.move.line']

        # Return all the account move lines to be reconciled in the previous sudo state, sorted to facilitate the pairing
        return lines_to_reconcile_sudo.sorted(lambda line: abs(line.balance)).sudo(self.env.is_superuser())
