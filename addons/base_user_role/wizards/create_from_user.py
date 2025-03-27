from odoo import fields, models


class WizardCreateRoleFromUser(models.TransientModel):
    _name = "wizard.create.role.from.user"
    _description = "Create role from user wizard"

    name = fields.Char(required=True)
    assign_to_user = fields.Boolean("Assign to user", default=True)

    def create_from_user(self):
        self.ensure_one()

        user_ids = self.env.context.get("active_ids", [])
        assert len(user_ids) == 1

        user_id = user_ids[0]

        role_obj = self.env["res.users.role"]
        role_line_obj = self.env["res.users.role.line"]
        user_obj = self.env["res.users"]

        user = user_obj.browse(user_id)

        role = role_obj.create(
            {
                "name": self.name,
            }
        )

        role.implied_ids = [(6, 0, user.groups_id.ids)]

        if self.assign_to_user:
            role_line_obj.create(
                {
                    "role_id": role.id,
                    "user_id": user_id,
                }
            )

        return {
            "context": self.env.context,
            "name": "Role",
            "view_type": "form",
            "view_mode": "form",
            "res_model": "res.users.role",
            "res_id": role.id,
            "target": "current",
            "type": "ir.actions.act_window",
        }
