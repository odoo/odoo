# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _, Command
from odoo.exceptions import AccessError, UserError

import logging


_logger = logging.getLogger(__name__)


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    expense_sheet_ids = fields.One2many(
        'hr.expense.sheet', 'payslip_id', string='Expenses',
        help="Expenses to reimburse to employee.")
    expenses_count = fields.Integer(compute='_compute_expenses_count', compute_sudo=True)

    def _compute_input_line_ids(self):
        super()._compute_input_line_ids()
        # Else it would generate lines for expenses of another payslip
        if not self.env.context.get('payslip_batch_creation'):
            self._update_expense_input_line_ids_without_linking()

    @api.depends('expense_sheet_ids')
    def _compute_expenses_count(self):
        for payslip in self:
            payslip.expenses_count = len(payslip.expense_sheet_ids)

    def action_payslip_cancel(self):
        # Remove the link to the cancelled payslip so it can be linked to another payslip
        # EXTENDS hr_payroll
        res = super().action_payslip_cancel()
        if self.expense_sheet_ids.account_move_ids:
            self.expense_sheet_ids._do_reverse_moves()
        self.expense_sheet_ids.payslip_id = False
        self._update_expense_input_line_ids()
        return res

    def action_payslip_draft(self):
        # We can add the new or previously unlinked expenses to the payslip
        # EXTENDS hr_payroll
        res = super().action_payslip_draft()
        self._link_expenses_to_payslip(clear_existing=False)  # Add the new expenses to the payslip, but keep the already linked ones
        return res

    def _create_account_move(self, values):
        # EXTENDS hr_payroll
        expense_rules = self.filtered('expense_sheet_ids').struct_id.rule_ids.filtered(lambda rule: rule.code == 'EXPENSES')
        if self.expense_sheet_ids and not expense_rules:
            raise UserError(_(
                "No salary rule was found to handle expenses in structure '%(structure_name)s'.",
                structure_name=self.struct_id.name
            ))

        if expense_rules and not expense_rules.filtered(lambda rule: rule.account_debit and rule.account_debit.account_type == 'liability_payable'):
            raise UserError(_(
                "The salary rules with the code 'EXPENSES' must have a debit account set to be able to properly "
                "reimburse the linked expenses. This must be an account of type 'Payable'."
            ))
        return super()._create_account_move(values)

    @api.model_create_multi
    def create(self, vals_list):
        # EXTENDS hr_payroll
        payslips = super().create(vals_list)
        draft_slips = payslips.filtered(lambda p: p.employee_id and p.state == 'draft')
        if not draft_slips:
            return payslips
        draft_slips._link_expenses_to_payslip()
        return payslips

    def write(self, vals):
        # EXTENDS hr_payroll
        res = super().write(vals)
        if 'expense_sheet_ids' in vals:
            self._update_expense_input_line_ids()
        if 'input_line_ids' in vals:
            self._update_expense_sheets()
        return res

    def _get_employee_sheets_to_refund_in_payslip(self):
        return self.env['hr.expense.sheet'].sudo().search([
            ('employee_id', 'in', self.employee_id.ids),
            ('state', '=', 'approve'),
            ('payment_mode', '=', 'own_account'),
            ('refund_in_payslip', '=', True),
            ('payslip_id', '=', False)])

    def _link_expenses_to_payslip(self, clear_existing=True):
        """
        Link expenses to a payslip if the payslip is in draft state and the expense is not already linked to a payslip.
        """
        if not (self.env.is_superuser() or self.env.user.has_group('hr_payroll.group_hr_payroll_user')):
            raise AccessError(_(
                "You don't have the access rights to link an expense report to a payslip. You need to be a payroll officer to do that.")
            )

        sheets_sudo = self._get_employee_sheets_to_refund_in_payslip()
        # group by employee
        sheets_by_employee = sheets_sudo.grouped('employee_id')
        for slip_sudo in self.sudo():
            employee_sudo = slip_sudo.employee_id
            if employee_sudo in sheets_by_employee:
                if not slip_sudo.struct_id.rule_ids.filtered(lambda rule: rule.code == 'EXPENSES'):
                    continue
                payslip_sheets = sheets_by_employee[employee_sudo]
                if slip_sudo.expense_sheet_ids and clear_existing:
                    slip_sudo.expense_sheet_ids = [Command.set(payslip_sheets.ids)]
                elif payslip_sheets:
                    slip_sudo.expense_sheet_ids = [Command.link(sheet.id) for sheet in payslip_sheets]
                del sheets_by_employee[employee_sudo]  # To avoid double assignations

    def _update_expense_input_line_ids(self):
        expense_type = self.env.ref('hr_payroll_expense.expense_other_input', raise_if_not_found=False)
        if not expense_type:
            _logger.warning("The 'hr_payroll_expense.expense_other_input' payslip input type is missing.")
            return  # We cannot do anything without the expense type
        for payslip in self:
            # Sudo to bypass access rights, as we just need to read the expense sheet's total amounts
            total = sum(payslip.sudo().expense_sheet_ids.mapped('total_amount'))
            lines_to_remove = payslip.input_line_ids.filtered(lambda x: x.input_type_id == expense_type)
            input_lines_vals = [Command.delete(line.id) for line in lines_to_remove]
            if total:
                input_lines_vals.append(Command.create({
                    'amount': total,
                    'input_type_id': expense_type.id
                }))
            payslip.input_line_ids = input_lines_vals

    def _update_expense_input_line_ids_without_linking(self):
        """
        Includes expenses in input_line_ids of the payslip without linking the expense sheets to the payslip.
        """
        expense_type = self.env.ref('hr_payroll_expense.expense_other_input', raise_if_not_found=False)
        if not expense_type:
            _logger.warning("The 'hr_payroll_expense.expense_other_input' payslip input type is missing.")
            return

        sheets_sudo = self._get_employee_sheets_to_refund_in_payslip()
        sheets_by_employee = sheets_sudo.grouped('employee_id')
        for slip_sudo in self.sudo():
            if not slip_sudo.struct_id.rule_ids.filtered(lambda rule: rule.code == 'EXPENSES'):
                continue
            payslip_sheets = slip_sudo.expense_sheet_ids or \
                sheets_by_employee.get(slip_sudo.employee_id, self.env['hr.expense.sheet'])
            total = sum(payslip_sheets.mapped('total_amount'))
            lines_to_remove = slip_sudo.input_line_ids.filtered(lambda x: x.input_type_id == expense_type)
            input_lines_vals = [Command.delete(line.id) for line in lines_to_remove]
            if total:
                input_lines_vals.append(Command.create({
                    'amount': total,
                    'input_type_id': expense_type.id
                }))
            slip_sudo.input_line_ids = input_lines_vals

    def _update_expense_sheets(self):
        expense_type = self.env.ref('hr_payroll_expense.expense_other_input', raise_if_not_found=False)
        if not expense_type:
            return  # We cannot do anything without the expense type
        for payslip_sudo in self.sudo():
            if not payslip_sudo.input_line_ids.filtered(lambda line: line.input_type_id == expense_type):
                # Sudo to bypass access rights, as we just need to unlink the two models
                payslip_sudo.expense_sheet_ids.payslip_id = False

    def action_open_expenses(self):
        self.ensure_one()
        return_action = {
            'type': 'ir.actions.act_window',
            'name': _('Reimbursed Expenses'),
            'res_model': 'hr.expense.sheet',
        }
        if len(self.expense_sheet_ids.ids) > 1:
            return_action.update({
                'view_mode': 'list,form',
                'domain': [('id', 'in', self.expense_sheet_ids.ids)],
            })
        else:
            return_action.update({
                'view_mode': 'form',
                'res_id': self.expense_sheet_ids.id,
            })
        return return_action
