# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError


class ResRole(models.Model):
    _name = "res.role"
    _description = (
        "Represents a role in the system used to categorize users. "
        "Each role has a unique name and can be associated with multiple users. "
        "Roles can be mentioned in messages to notify all associated users."
    )
    _order = "sequence, id"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    user_ids = fields.Many2many("res.users", relation="res_role_res_users_rel", string="Users")
    user_ids_count = fields.Integer(compute="_compute_user_ids_count")
    # Stored as a Char instead of an Integer because the ORM couldn't distinguish between setting
    # the color to black (0) and unsetting the value (NULL).
    color = fields.Char(
        help="The color in which the usernames of people with this role will be displayed. "
        "If a user has multiple roles, the color of the first role (as determined by "
        "the sequence field) that has a color is used."
    )
    sequence = fields.Integer(default=10)

    _unique_name = models.UniqueIndex("(name)", "A role with the same name already exists.")
    # The color is eventually used to style the page. Ensure nothing harmful (e.g. CSS injection)
    # can be saved to this field.
    _valid_color_check = models.Constraint(
        "CHECK(color IS NULL OR color ~ '^#[A-Fa-f0-9]{6}$')",
        "The color must be a valid 6-digit hex code."
    )

    @api.depends("user_ids")
    def _compute_user_ids_count(self):
        user_count_by_role = dict(
            self.env["res.users"]._read_group(
                [("role_ids", "in", self.ids)], ["role_ids"], ["__count"],
            ),
        )
        for role in self:
            role.user_ids_count = user_count_by_role.get(role, 0)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_linked_activities(self):
        """ Prevent deletion of roles that are still in use as defaults or on unassigned activities. """
        blocking_items = []
        if unassigned := self.env['mail.activity'].sudo().search_count(
            [('role_id', 'in', self.ids), ('user_id', '=', False)]
        ):
            blocking_items.append(self.env._("%(count)s unassigned activity(ies)", count=unassigned))
        if act_types := self.env['mail.activity.type'].sudo().search([('default_role_id', 'in', self.ids)]):
            blocking_items.append(self.env._("Activity Types: %(types)s", types=act_types.mapped('name')))
        if plans := self.env['mail.activity.plan.template'].sudo().search([('role_id', 'in', self.ids)]):
            blocking_items.append(self.env._("Activity Plans: %(plans)s", plans=plans.mapped('display_name')))
        if server_actions := self.env['ir.actions.server'].sudo().search_count([('activity_role_id', 'in', self.ids)]):
            blocking_items.append(self.env._("%(count)s Server Action(s)", count=server_actions))
        if blocking_items:
            raise UserError(
                self.env._(
                    "You cannot delete these roles because they are still in use in:\n"
                    "- %(blocking_list)s\n\n"
                    "Please archive the role(s) instead, or reassign these items.",
                    blocking_list="\n- ".join(blocking_items)
                )
            )
