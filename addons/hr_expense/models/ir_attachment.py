from collections.abc import Collection

from odoo import api, models
from odoo.exceptions import AccessError
<<<<<<< ad45fb0c110890d0df633012483e428a402bb6da
||||||| 01e3f58492fa045c82279acefc9e704ce090117c
from odoo.tools.misc import clean_context
=======
from odoo.tools.misc import clean_context
from odoo.addons.hr_expense.wizard.hr_expense_split_wizard import _COPY_ATTACHMENT_FROM_SPLIT_WIZARD
>>>>>>> 713650737160372bdd5c4f9d41bfb659596c26bb


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.ondelete(at_uninstall=False)
    def _prevent_delete_from_submitted_expense(self):
        expense_attachments = self.filtered(lambda a: a.res_model == 'hr.expense' and a.res_id)
        expenses = self.env['hr.expense'].browse(expense_attachments.mapped('res_id'))
        if not all(
            (expense.exists() and expense.state in {'draft', 'submitted'} and expense.has_access('write')) or self.env.su
            for expense in expenses
        ):
            raise AccessError(self.env._("You can't delete attachments from an expense once it has been submitted."))

<<<<<<< ad45fb0c110890d0df633012483e428a402bb6da
    def _inaccessible_comodel_records(self, model_and_ids: dict[str, Collection[int]], operation: str):
        expense_ids = list(filter(None, model_and_ids.get('hr.expense', [])))
        expenses = self.env['hr.expense'].browse(expense_ids)
        accessible_user_expense_ids = set(expenses._filtered_access('read').filtered(
            lambda e: e.state in {'draft', 'submitted'} and e.employee_id.user_id == self.env.user
        ).ids)
        blocked_expense_ids = []
        if operation != 'read' and not self.env.su:
            blocked_expense_ids = expenses.filtered(  # Attachments cannot be added/modified once an expense has been posted
                lambda e: not (e.id in accessible_user_expense_ids or (e.state in {'draft', 'submitted'} and e.has_access('write'))),
            ).ids
            for expense_id in blocked_expense_ids:
                yield 'hr.expense', expense_id
||||||| 01e3f58492fa045c82279acefc9e704ce090117c
    @api.model_create_multi
    def create(self, vals_list):
        expense_attachments = [vals for vals in vals_list if vals.get('res_model') == 'hr.expense' and vals.get('res_id')]
        expenses = self.env['hr.expense'].browse([vals['res_id'] for vals in expense_attachments])
        if not all(
            (expense.state in {'draft', 'submitted'} and (expense.has_access('write') or expense.employee_id.user_id == self.env.user)) or self.env.su
            for expense in expenses
        ):
            raise AccessError(self.env._("You can't add attachments to an expense once it has been approved."))
=======
    @api.model_create_multi
    def create(self, vals_list):
        expense_attachments = [vals for vals in vals_list if vals.get('res_model') == 'hr.expense' and vals.get('res_id')]
        expenses = self.env['hr.expense'].browse([vals['res_id'] for vals in expense_attachments])
        if not (self.env.context.get('from_split_wizard') is _COPY_ATTACHMENT_FROM_SPLIT_WIZARD or all(
            (expense.state in {'draft', 'submitted'} and (expense.has_access('write') or expense.employee_id.user_id == self.env.user)) or self.env.su
            for expense in expenses
        )):
            raise AccessError(self.env._("You can't add attachments to an expense once it has been approved."))
>>>>>>> 713650737160372bdd5c4f9d41bfb659596c26bb

        model_and_ids = {
            **model_and_ids,
            'hr.expense': [id_ for id_ in expense_ids if id_ not in blocked_expense_ids and id_ not in accessible_user_expense_ids],
        }
        yield from super()._inaccessible_comodel_records(model_and_ids, operation)

    def _has_attachments_ownership(self, attachment_tokens):
        expense_attachments = self.filtered(lambda a: a.has_access('read') and a.res_model == 'hr.expense' and a.res_id)
        expenses = self.env['hr.expense'].browse(expense_attachments.mapped('res_id'))
        if expenses.filtered(lambda e: e.state == 'submitted' and e.employee_id.user_id == self.env.user) and not self.env.su:
            return False
        return super()._has_attachments_ownership(attachment_tokens)
