from odoo import api, models
from odoo.exceptions import AccessError


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    @api.ondelete(at_uninstall=False)
    def _prevent_delete_from_submitted_expense(self):
        expense_attachments = self.filtered(lambda a: a.res_model == 'hr.expense' and a.res_id)
        expenses = self.env['hr.expense'].browse(expense_attachments.mapped('res_id'))
        if not all(
            (expense.state in {'draft', 'submitted'} and expense.has_access('write')) or self.env.su
            for expense in expenses
        ):
            raise AccessError(self.env._("You can't delete attachments from an expense once it has been submitted."))

    @api.model_create_multi
    def create(self, vals_list):
        expense_attachments = [vals for vals in vals_list if vals.get('res_model') == 'hr.expense' and vals.get('res_id')]
        expenses = self.env['hr.expense'].browse([vals['res_id'] for vals in expense_attachments])
        if not all(
            (expense.state in {'draft', 'submitted'} and (expense.has_access('write') or expense.employee_id.user_id == self.env.user)) or self.env.su
            for expense in expenses
        ):
            raise AccessError(self.env._("You can't add attachments to an expense once it has been approved."))

        user_expenses = expenses.filtered(lambda expense: expense.employee_id.user_id == self.env.user)
        user_expense_attachments = [
            vals for vals in expense_attachments
            if vals['res_id'] in user_expenses.ids and not expenses.browse(vals['res_id']).has_access('write')  # to not over sudo
        ]
        attachments = super(IrAttachment, self.sudo()).create(user_expense_attachments).sudo(self.env.su)

        remaining_vals_list = [vals for vals in vals_list if vals not in user_expense_attachments]
        if remaining_vals_list:
            attachments += super().create(remaining_vals_list)
        return attachments
