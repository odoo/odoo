# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    group_l10n_ph_discount_privilege = fields.Boolean(
        string="Discount Privileges",
        implied_group="l10n_ph.group_l10n_ph_discount_privilege",
        group="account.group_account_manager",
    )

    @api.onchange("group_l10n_ph_discount_privilege")
    def _onchange_group_l10n_ph_discount_privilege(self):
        if (
            "group_discount_per_so_line" in self._fields
            and self.group_l10n_ph_discount_privilege
        ):
            self.group_discount_per_so_line = True
