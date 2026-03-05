from odoo import models
from odoo.exceptions import UserError


class ResCompany(models.Model):
    _inherit = "res.company"

    def action_open_lock_date_wizard(self):
        self.ensure_one()
        if not self.env.user.has_group(
            "gov_account_lock_date_update.group_account_lock_date_manager"
        ):
            raise UserError("You are not allowed to update lock dates.")

        action = self.env.ref(
            "gov_account_lock_date_update.account_lock_date_update_wizard_action",
            raise_if_not_found=False,
        )
        if not action:
            return False
        values = action.read()[0]
        values["context"] = {
            "default_company_id": self.id,
            "default_new_lock_date": self.fiscalyear_lock_date,
        }
        return values


