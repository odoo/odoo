# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ResUsers(models.Model):
    _inherit = "res.users"

    onsip_auth_username = fields.Char(
        related="res_users_settings_id.onsip_auth_username", inverse="_inverse_onsip_auth_username", related_sudo=False
    )

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ["onsip_auth_username"]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ["onsip_auth_username"]

    def _inverse_onsip_auth_username(self):
        for user in self:
            res_users_settings_record = self.env["res.users.settings"]._find_or_create_for_user(user)
            res_users_settings_record.onsip_auth_username = user.onsip_auth_username
