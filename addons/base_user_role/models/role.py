# Copyright 2014 ABF OSIELL <http://osiell.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
import datetime
import logging

from odoo import SUPERUSER_ID, _, api, fields, models

_logger = logging.getLogger(__name__)


class ResUsersRole(models.Model):
    _name = "res.users.role"
    _inherits = {"res.groups": "group_id"}
    _description = "User role"

    group_id = fields.Many2one(
        comodel_name="res.groups",
        required=True,
        ondelete="cascade",
        readonly=True,
        string="Associated group",
    )
    line_ids = fields.One2many(
        comodel_name="res.users.role.line", inverse_name="role_id", string="Role lines"
    )
    user_ids = fields.One2many(
        comodel_name="res.users", string="Users list", compute="_compute_user_ids"
    )
    rule_ids = fields.Many2many(
        comodel_name="ir.rule",
        compute="_compute_rule_ids",
        string="Record Rules",
        required=False,
    )
    rules_count = fields.Integer(compute="_compute_rule_ids")
    model_access_ids = fields.Many2many(
        comodel_name="ir.model.access",
        compute="_compute_model_access_ids",
        string="Access Rights",
        required=False,
    )
    model_access_count = fields.Integer(compute="_compute_model_access_ids")
    group_category_id = fields.Many2one(
        related="group_id.category_id",
        default=lambda cls: cls.env.ref("base_user_role.ir_module_category_role").id,
        string="Associated category",
        help="Associated group's category",
        readonly=False,
    )

    @api.depends("line_ids.user_id")
    def _compute_user_ids(self):
        for role in self.sudo() if self._bypass_rules() else self:
            role.user_ids = role.line_ids.mapped("user_id")

    @api.depends("implied_ids", "implied_ids.model_access")
    def _compute_model_access_ids(self):
        for rec in self:
            rec.model_access_ids = rec.implied_ids.model_access.ids
            rec.model_access_count = len(rec.model_access_ids)

    @api.depends("implied_ids", "implied_ids.rule_groups")
    def _compute_rule_ids(self):
        for rec in self:
            rec.rule_ids = rec.implied_ids.rule_groups.ids
            rec.rules_count = len(rec.rule_ids)

    @api.model
    def _bypass_rules(self):
        # Run methods as super user to avoid problems by "Administrator/Access Right"
        return self._name == "res.users.role" and self.env.user.has_group(
            "base.group_erp_manager"
        )

    @api.model_create_multi
    def create(self, vals_list):
        model = (self.sudo() if self._bypass_rules() else self).browse()
        new_records = super(ResUsersRole, model).create(vals_list)
        new_records.update_users()
        return new_records

    def read(self, fields=None, load="_classic_read"):
        recs = self.sudo() if self._bypass_rules() else self
        return super(ResUsersRole, recs).read(fields, load)

    def write(self, vals):
        recs = self.sudo() if self._bypass_rules() else self
        # Workaround to solve issue with broken code in odoo that clear the
        # cache during the write: see odoo/addons/base/models/res_users.py#L226
        groups_vals = {}
        for field in recs.group_id._fields:
            if field in vals:
                groups_vals[field] = vals.pop(field)
        if groups_vals:
            recs.group_id.write(groups_vals)
        res = super(ResUsersRole, recs).write(vals)
        recs.update_users()
        return res

    def unlink(self):
        users = self.mapped("user_ids")
        res = super(ResUsersRole, self).unlink()
        users.set_groups_from_roles(force=True)
        return res

    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {}, name=_("%s (copy)", self.name))
        return super().copy(default)

    def update_users(self):
        """Update all the users concerned by the roles identified by `ids`."""
        users = self.mapped("user_ids")
        users.set_groups_from_roles()
        return True

    @api.model
    def cron_update_users(self):
        logging.info("Update user roles")
        self.search([]).update_users()

    def show_rule_ids(self):
        action = self.env["ir.actions.actions"]._for_xml_id("base.action_rule")
        action["domain"] = [("id", "in", self.rule_ids.ids)]
        return action

    def show_model_access_ids(self):
        action = self.env["ir.actions.actions"]._for_xml_id("base.ir_access_act")
        action["domain"] = [("id", "in", self.model_access_ids.ids)]
        return action


class ResUsersRoleLine(models.Model):
    _name = "res.users.role.line"
    _description = "Users associated to a role"

    active = fields.Boolean(related="user_id.active")
    role_id = fields.Many2one(
        comodel_name="res.users.role", required=True, string="Role", ondelete="cascade"
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        required=True,
        string="User",
        domain=[("id", "!=", SUPERUSER_ID)],
        ondelete="cascade",
    )
    date_from = fields.Date("From")
    date_to = fields.Date("To")
    is_enabled = fields.Boolean("Enabled", compute="_compute_is_enabled")
    _sql_constraints = [
        (
            "user_role_uniq",
            "unique (user_id,role_id)",
            "Roles can be assigned to a user only once at a time",
        )
    ]

    @api.depends("date_from", "date_to")
    def _compute_is_enabled(self):
        today = datetime.date.today()
        for role_line in self:
            role_line.is_enabled = True
            if role_line.date_from:
                date_from = role_line.date_from
                if date_from > today:
                    role_line.is_enabled = False
            if role_line.date_to:
                date_to = role_line.date_to
                if today > date_to:
                    role_line.is_enabled = False

    def unlink(self):
        users = self.mapped("user_id")
        res = super(ResUsersRoleLine, self).unlink()
        users.set_groups_from_roles(force=True)
        return res
