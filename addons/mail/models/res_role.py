import typing

from odoo import fields, models

if typing.TYPE_CHECKING:
    from odoo.addons.bus.models.res_users import ResUsers


class ResRole(models.Model):
    _name = "res.role"
    _description = (
        "Represents a role in the system used to categorize users. "
        "Each role has a unique name and can be associated with multiple users. "
        "Roles can be mentioned in messages to notify all associated users."
    )

    name = fields.Char(required=True)
    user_ids: ResUsers = fields.Many2many(
        comodel_name="res.users",
        relation="res_role_res_users_rel",
        string="Users",
    )

    _unique_name = models.UniqueIndex(
        "(name)", "A role with the same name already exists."
    )
