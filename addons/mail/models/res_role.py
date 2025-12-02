# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResRole(models.Model):
    _name = "res.role"
    _description = (
        "Represents a role in the system used to categorize users. "
        "Each role has a unique name and can be associated with multiple users. "
        "Roles can be mentioned in messages to notify all associated users."
    )

    name = fields.Char(required=True)
    user_ids = fields.Many2many("res.users", relation="res_role_res_users_rel", string="Users")
    user_ids_count = fields.Integer(compute="_compute_user_ids_count")

    _unique_name = models.UniqueIndex("(name)", "A role with the same name already exists.")

    @api.depends("user_ids")
    def _compute_user_ids_count(self):
        user_count_by_role = dict(
            self.env["res.users"]._read_group(
                [("role_ids", "in", self.ids)], ["role_ids"], ["__count"],
            ),
        )
        for role in self:
            role.user_ids_count = user_count_by_role.get(role, 0)
