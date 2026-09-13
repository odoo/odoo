from odoo import api, fields, models
from odoo.exceptions import RedirectWarning, UserError

from ..tools import debug_log as dbg
from odoo.addons.mail.tools.discuss import Store


class ResPartner(models.Model):
    _inherit = "res.partner"

    employee_ids = fields.One2many(
        comodel_name="hr.employee",
        inverse_name="partner_id",
        string="Employees",
        groups="hr.group_hr_user",
        help="Related employees based on their private address",
    )
    employees_count = fields.Integer(
        compute="_compute_employees_count",
        groups="hr.group_hr_user",
    )
    employee = fields.Boolean(
        compute="_compute_employee",
        search="_search_employee",
        help="Whether this contact is an Employee.",
    )

    # What a person IS, kept where an employee's confidential facts already
    # live: on the private facet, a child partner behind its own record rule.
    # They are declared by hr because hr owns their vocabulary and is their
    # only reader; base owns the facet and its rule.
    place_of_birth = fields.Char()
    country_of_birth = fields.Many2one(comodel_name="res.country")
    marital = fields.Selection(
        selection="_selection_marital_status",
        string="Marital Status",
        default="single",
    )
    spouse_complete_name = fields.Char(string="Spouse Legal Name")
    spouse_birthdate = fields.Date()
    dependent_children = fields.Integer()
    education_certificate = fields.Selection(
        selection="_selection_certificate",
        string="Certificate Level",
    )
    study_field = fields.Char(string="Field of Study")
    study_school = fields.Char(string="School")

    def _selection_marital_status(self):
        return [
            ("single", self.env._("Single")),
            ("married", self.env._("Married")),
            ("cohabitant", self.env._("Legal Cohabitant")),
            ("widower", self.env._("Widower")),
            ("divorced", self.env._("Divorced")),
        ]

    def _selection_certificate(self):
        return [
            ("graduate", self.env._("Graduate")),
            ("bachelor", self.env._("Bachelor")),
            ("master", self.env._("Master")),
            ("doctor", self.env._("Doctor")),
            ("other", self.env._("Other")),
        ]

    @dbg.timed
    def _compute_employees_count(self):
        counts = dict(
            self.env["hr.employee"]
            .sudo()
            ._read_group(
                [
                    ("partner_id", "in", self.ids),
                    ("company_id", "in", self.env.companies.ids),
                ],
                groupby=["partner_id"],
                aggregates=["__count"],
            )
        )
        for partner in self:
            partner.employees_count = counts.get(partner, 0)

    def action_view_employees(self):
        self.check_singleton()
        if self.employees_count > 1:
            return {
                "name": self.env._("Related Employees"),
                "type": "ir.actions.act_window",
                "res_model": "hr.employee",
                "view_mode": "kanban",
                "domain": [
                    ("id", "in", self.employee_ids.ids),
                    ("company_id", "in", self.env.companies.ids),
                ],
            }
        return {
            "name": self.env._("Employee"),
            "type": "ir.actions.act_window",
            "res_model": "hr.employee",
            "res_id": self.employee_ids.filtered(
                lambda e: e.company_id in self.env.companies
            ).id,
            "view_mode": "form",
        }

    def _get_all_addr(self):
        # An employee's home address is a private child of their work contact,
        # so this reads the child's own address rather than
        # six prefixed columns on the employee. It keeps the "employee" contact
        # type the ISO20022 and batch-payment callers already expect, and still
        # puts the home address first.
        self.check_singleton()
        private = self.child_ids.filtered(lambda partner: partner.type == "private")
        if not private:
            return super()._get_all_addr()
        dbg.logic.debug(
            "[party:%s] _get_all_addr: home address from private child %s first",
            self.id,
            private[0].id,
        )
        home = dict(private[0]._get_all_addr()[0], contact_type="employee")
        return [home] + super()._get_all_addr()

    @dbg.timed
    @api.depends("employee_ids")
    def _compute_employee(self):
        employee_data = (
            self.env["hr.employee"]
            .sudo()
            ._read_group(
                domain=[("partner_id", "in", self.ids)],
                groupby=["partner_id"],
            )
        )
        employees = {employee for [employee] in employee_data}
        for partner in self:
            partner.employee = partner in employees

    def _search_employee(self, operator, value):
        if operator not in ("=", "!=") or not isinstance(value, bool):
            raise NotImplementedError
        has_employee = (operator == "=") == value
        employed = self.env["hr.employee"].sudo()._search([])
        return [
            ("id", "in" if has_employee else "not in", employed.subselect("partner_id"))
        ]

    @api.ondelete(at_uninstall=False)
    def _unlink_contact_rel_employee(self):
        partners = self.filtered(lambda partner: partner.sudo().employee_ids)
        dbg.logic.debug(
            "res.partner.unlink %s: %s are linked to employees",
            dbg.rec(self),
            dbg.rec(partners),
        )
        if len(self) == 1 and len(partners) == 1 and self.id == partners[0].id:
            raise UserError(
                self.env._(
                    "You cannot delete contact that are linked to an employee, please archive them instead."
                )
            )
        if partners:
            error_msg = self.env._(
                "You cannot delete contact(s) linked to employee(s).\n"
                "Please archive them instead.\n\n"
                "Affected contact(s): %(names)s",
                names=", ".join([u.name for u in partners]),
            )
            action_error = partners._action_show()
            raise RedirectWarning(error_msg, action_error, self.env._("Go to contact"))

    def _action_show(self):
        view_id = self.env.ref("base.view_partner_form").id
        action = {
            "type": "ir.actions.act_window",
            "res_model": "res.partner",
            "context": {"create": False},
        }
        if len(self) > 1:
            action.update(
                {
                    "name": self.env._("Contacts"),
                    "view_mode": "list,form",
                    "views": [[None, "list"], [view_id, "form"]],
                    "domain": [("id", "in", self.ids)],
                }
            )
        else:
            action.update(
                {
                    "view_mode": "form",
                    "views": [[view_id, "form"]],
                    "res_id": self.id,
                }
            )
        return action

    def _get_fields_store_avatar_card(self, target):
        avatar_card_fields = super()._get_fields_store_avatar_card(target)
        if target.is_internal(self.env):
            dbg.logic.debug(
                "res.partner avatar card on %s: internal target, employee fields added",
                dbg.rec(self),
            )
            employee_fields = self.sudo().employee_ids._get_fields_store_avatar_card(
                target
            )
            avatar_card_fields.append(
                Store.Many("employee_ids", employee_fields, mode="ADD", sudo=True)
            )
        return avatar_card_fields
