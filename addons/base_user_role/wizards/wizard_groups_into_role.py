# Copyright 2021 Sodexis
# License OPL-1 (See LICENSE file for full copyright and licensing details).


from odoo import fields, models


class GroupGroupsIntoRole(models.TransientModel):
    """
    This wizard is used to group different groups into a role.
    """

    _name = "wizard.groups.into.role"
    _description = "Group groups into a role"
    name = fields.Char(
        required=True,
        help="Group groups into a role and specify a name for this role",
    )

    def create_role(self):
        selected_group_ids = self.env.context.get("active_ids", [])
        vals = {
            "name": self.name,
            "implied_ids": selected_group_ids,
        }
        role = self.env["res.users.role"].create(vals)

        return {
            "type": "ir.actions.act_window",
            "res_model": "res.users.role",
            "view_mode": "form",
            "res_id": role.id,
            "target": "current",
            "context": {
                "form_view_ref": "base_user_role.view_res_users_role_form",
            },
        }
