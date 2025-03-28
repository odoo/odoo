# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResRole(models.Model):
    _name = "res.role"
    _description = (
        "Represents a role in the system used to categorize users. "
        "Each role has a unique name and can be associated with multiple users. "
        "Roles can be mentioned in messages to notify all associated users."
    )

    name = fields.Char(required=True)
    user_ids = fields.Many2many("res.users", relation="res_role_res_users_rel", string="Users")

    _unique_name = models.UniqueIndex("(name)", "A role with the same name already exists.")
