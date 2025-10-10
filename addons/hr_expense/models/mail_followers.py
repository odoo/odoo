from odoo import models


class MailFollowers(models.Model):
    _inherit = 'mail.followers'

    def _add_default_followers_filter_partner_subtypes(self, res_model, res_ids, partner_subtypes):
        super()._add_default_followers_filter_partner_subtypes(res_model, res_ids, partner_subtypes)
        if res_model == 'hr.expense' and res_ids:
            expenses = self.env[res_model].browse(res_ids)
            state_subtype_ids = set((
                self.env.ref('hr_expense.mt_expense_reset', raise_if_not_found=False) +
                self.env.ref('hr_expense.mt_expense_refused', raise_if_not_found=False) +
                self.env.ref('hr_expense.mt_expense_paid', raise_if_not_found=False) +
                self.env.ref('hr_expense.mt_expense_entry_draft', raise_if_not_found=False) +
                self.env.ref('hr_expense.mt_expense_entry_delete', raise_if_not_found=False) +
                self.env.ref('hr_expense.mt_expense_approved', raise_if_not_found=False)
            ).ids)
            for expense in expenses:
                # We don't want to notify the manager when the state changes
                manager_pid = expense.manager_id.partner_id.id
                if manager_pid in partner_subtypes:
                    partner_subtypes[manager_pid] = list(set(partner_subtypes[manager_pid]) - set(state_subtype_ids))
