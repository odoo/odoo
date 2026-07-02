# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def _load_pos_data_read(self, records, config):
        read_records = super()._load_pos_data_read(records, config)
        extra_by_id = {
            user.id: {
                "_l10n_ph_pos_allow_self_line_void": bool(
                    user.employee_id.l10n_ph_pos_allow_self_line_void,
                ),
                "_l10n_ph_cashier_employee_id": user.employee_id.id or False,
            }
            for user in records.sudo()
        }
        for user_data in read_records:
            user_data.update(extra_by_id.get(user_data["id"], {}))
        return read_records
