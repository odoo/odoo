# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_ph_enable_discount_privilege = fields.Boolean(
        string="Discount Privileges",
        related="company_id.l10n_ph_enable_discount_privilege",
        readonly=False,
        group="account.group_account_manager",
    )

    def set_values(self):
        super().set_values()
        group = self.env.ref("l10n_ph.group_l10n_ph_discount_privilege")
        users = self.env["res.users"].search(
            [
                "|",
                ("company_id", "=", self.company_id.id),
                ("company_ids", "in", self.company_id.id),
            ],
        )
        if self.l10n_ph_enable_discount_privilege:
            users_not_in_group = users.filtered(lambda u: group not in u.group_ids)
            if users_not_in_group:
                users_not_in_group.write({"group_ids": [(4, group.id)]})
        else:
            users_in_group = users.filtered(lambda u: group in u.group_ids)
            if users_in_group:
                users_in_group.write({"group_ids": [(3, group.id)]})

    @api.onchange("l10n_ph_enable_discount_privilege")
    def _onchange_l10n_ph_enable_discount_privilege(self):
        if (
            "group_discount_per_so_line" in self._fields
            and self.l10n_ph_enable_discount_privilege
        ):
            self.group_discount_per_so_line = True
