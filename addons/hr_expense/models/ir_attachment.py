from collections.abc import Collection

from odoo import api, models
from odoo.exceptions import AccessError


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.ondelete(at_uninstall=False)
    def _prevent_delete_from_submitted_expense(self):
        expense_attachments = self.filtered(lambda a: a.res_model == 'hr.expense' and a.res_id)
        expenses = self.env['hr.expense'].browse(expense_attachments.mapped('res_id'))
        if not all(
            (expense.state in {'draft', 'submitted'} and expense.has_access('write')) or self.env.su
            for expense in expenses
        ):
            raise AccessError(self.env._("You can't delete attachments from an expense once it has been submitted."))

    def _inaccessible_comodel_records(self, model_and_ids: dict[str, Collection[int]], operation: str):
        expense_ids = list(filter(None, model_and_ids.get('hr.expense', [])))
        expenses = self.env['hr.expense'].browse(expense_ids)
        user_expenses = expenses.filtered(lambda e: e.state in {'draft', 'submitted'} and e.employee_id.user_id == self.env.user)

        blocked_expense_ids = []
        if operation != 'read' and not self.env.su:
            blocked_expense_ids = expenses.filtered(  # Attachments cannot be added/modified once an expense has been posted
                lambda e: not (e.id in user_expenses.ids or (e.state in {'draft', 'submitted'} and e.has_access('write'))),
            ).ids
            for expense_id in blocked_expense_ids:
                yield 'hr.expense', expense_id

        model_and_ids = {
            **model_and_ids,
            'hr.expense': [id_ for id_ in expense_ids if id_ not in blocked_expense_ids and id_ not in user_expenses.ids],
        }
        yield from super()._inaccessible_comodel_records(model_and_ids, operation)

    def _has_attachments_ownership(self, attachment_tokens):
        expense_attachments = self.filtered(lambda a: a.has_access('read') and a.res_model == 'hr.expense' and a.res_id)
        expenses = self.env['hr.expense'].browse(expense_attachments.mapped('res_id'))
        if expenses.filtered(lambda e: e.state == 'submitted' and e.employee_id.user_id == self.env.user) and not self.env.su:
            return False
        return super()._has_attachments_ownership(attachment_tokens)
