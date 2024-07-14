# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from odoo import api, fields, models, _, Command


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    expense_sheet_ids = fields.One2many(
        'hr.expense.sheet', 'payslip_id', string='Expenses',
        help="Expenses to reimburse to employee.")
    expenses_count = fields.Integer(compute='_compute_expenses_count')

    @api.depends('expense_sheet_ids.nb_expense', 'expense_sheet_ids.payslip_id')
    def _compute_expenses_count(self):
        for payslip in self:
            payslip.expenses_count = sum(payslip.mapped('expense_sheet_ids.nb_expense'))

    @api.model_create_multi
    def create(self, vals_list):
        payslips = super().create(vals_list)
        draft_slips = payslips.filtered(lambda p: p.employee_id and p.state == 'draft')
        if not draft_slips:
            return payslips
        sheets = self.env['hr.expense.sheet'].search([
            ('employee_id', 'in', draft_slips.mapped('employee_id').ids),
            ('state', '=', 'approve'),
            ('payment_mode', '=', 'own_account'),
            ('refund_in_payslip', '=', True),
            ('payslip_id', '=', False)])
        # group by employee
        sheets_by_employee = defaultdict(lambda: self.env['hr.expense.sheet'])
        for sheet in sheets:
            sheets_by_employee[sheet.employee_id] |= sheet
        for slip in draft_slips:
            payslip_sheets = sheets_by_employee[slip.employee_id]
            if slip.expense_sheet_ids:
                slip.expense_sheet_ids = [Command.set(payslip_sheets.ids)]
            elif payslip_sheets:
                slip.expense_sheet_ids = [Command.link(sheet.id) for sheet in payslip_sheets]
        return payslips

    def write(self, vals):
        res = super().write(vals)
        if 'expense_sheet_ids' in vals:
            self._compute_expense_input_line_ids()
        if 'input_line_ids' in vals:
            self._update_expense_sheets()
        return res

    def _compute_expense_input_line_ids(self):
        expense_type = self.env.ref('hr_payroll_expense.expense_other_input', raise_if_not_found=False)
        for payslip in self:
            total = sum(payslip.expense_sheet_ids.mapped('total_amount'))
            if not total or not expense_type:
                continue
            lines_to_remove = payslip.input_line_ids.filtered(lambda x: x.input_type_id == expense_type)
            input_lines_vals = [Command.delete(line.id) for line in lines_to_remove]
            input_lines_vals.append(Command.create({
                'amount': total,
                'input_type_id': expense_type.id
            }))
            payslip.update({'input_line_ids': input_lines_vals})

    def _update_expense_sheets(self):
        expense_type = self.env.ref('hr_payroll_expense.expense_other_input', raise_if_not_found=False)
        for payslip in self:
            if not payslip.input_line_ids.filtered(lambda line: line.input_type_id == expense_type):
                payslip.expense_sheet_ids.write({'payslip_id': False})

    def action_payslip_done(self):
        res = super(HrPayslip, self).action_payslip_done()
        for expense in self.expense_sheet_ids:
            expense.action_sheet_move_create()
            expense.set_to_paid()
            expense.payment_state = 'paid'
        return res

    def open_expenses(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reimbursed Expenses'),
            'res_model': 'hr.expense',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.mapped('expense_sheet_ids.expense_line_ids').ids)],
        }
