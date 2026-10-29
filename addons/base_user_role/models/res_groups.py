from odoo import api, fields, models


class ResGroups(models.Model):
    _inherit = "res.groups"

    view_access = fields.Many2many(
        groups="base.group_system",
    )

    # The inverse field of the field group_id on the res.users.role model
    # This field should be used a One2one relation as a role can only be
    # represented by one group. It's declared as a One2many field as the
    # inverse field on the res.users.role it's declared as a Many2one
    role_id = fields.One2many(
        comodel_name="res.users.role",
        inverse_name="group_id",
        help="Relation for the groups that represents a role",
    )

    role_ids = fields.Many2many(
        comodel_name="res.users.role",
        relation="res_groups_implied_roles_rel",
        string="Roles",
        compute="_compute_role_ids",
        help="Roles in which the group is involved",
    )

    parent_ids = fields.Many2many(
        "res.groups",
        "res_groups_implied_rel",
        "hid",
        "gid",
        string="Parents",
        help="Inverse relation for the Inherits field. "
        "The groups from which this group is inheriting",
    )

    trans_parent_ids = fields.Many2many(
        comodel_name="res.groups",
        string="Parent Groups",
        compute="_compute_trans_parent_ids",
        recursive=True,
    )

    role_count = fields.Integer("# Roles", compute="_compute_role_count")

    def _compute_role_count(self):
        for group in self:
            group.role_count = len(group.role_ids)

    @api.depends("parent_ids.trans_parent_ids")
    def _compute_trans_parent_ids(self):
        for group in self:
            group.trans_parent_ids = (
                group.parent_ids | group.parent_ids.trans_parent_ids
            )

    def _compute_role_ids(self):
        for group in self:
            if group.trans_parent_ids:
                group.role_ids = group.trans_parent_ids.role_id
            else:
                group.role_ids = group.role_id

    def action_view_roles(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "base_user_role.action_res_users_role_tree"
        )
        action["context"] = {}
        if len(self.role_ids) > 1:
            action["domain"] = [("id", "in", self.role_ids.ids)]
        elif self.role_ids:
            form_view = [
                (self.env.ref("base_user_role.view_res_users_role_form").id, "form")
            ]
            if "views" in action:
                action["views"] = form_view + [
                    (state, view) for state, view in action["views"] if view != "form"
                ]
            else:
                action["views"] = form_view
            action["res_id"] = self.role_ids.id
        else:
            action = {"type": "ir.actions.act_window_close"}
        return action
