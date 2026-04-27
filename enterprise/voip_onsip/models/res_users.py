from odoo import api, models, fields


class ResUsers(models.Model):
    _inherit = "res.users"

    onsip_auth_username = fields.Char(
        compute="_compute_onsip_auth_username",
        inverse="_reflect_change_in_res_users_settings",
        groups="base.group_user",
    )

    @api.depends("res_users_settings_id.onsip_auth_username")
    def _compute_onsip_auth_username(self):
        for user in self:
            user.onsip_auth_username = user.res_users_settings_id.onsip_auth_username

    @api.model
    def _get_voip_user_configuration_fields(self):
        return super()._get_voip_user_configuration_fields() + [
            "onsip_auth_username",
        ]
