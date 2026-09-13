from odoo import api, fields, models
from odoo.exceptions import UserError

from ..tools import debug_log as dbg


class MailActivityPlan(models.Model):
    _inherit = "mail.activity.plan"

    department_id = fields.Many2one(
        comodel_name="hr.department",
        compute="_compute_department_id",
        store=True,
        index="btree_not_null",
        readonly=False,
        ondelete="set null",
        check_company=True,
    )
    department_assignable = fields.Boolean(compute="_compute_department_assignable")

    @api.constrains("res_model")
    def _check_compatibility_with_model(self):
        plan_tocheck = self.filtered(lambda plan: not plan.department_assignable)
        failing_plans = plan_tocheck.filtered("department_id")
        dbg.logic.debug(
            "mail.activity.plan compatibility on %s: %s not department-assignable, "
            "%s carry a department",
            dbg.rec(self),
            dbg.rec(plan_tocheck),
            dbg.rec(failing_plans),
        )
        if failing_plans:
            raise UserError(
                self.env._(
                    "Plan %(plan_names)s cannot use a department as it is used only for some HR plans.",
                    plan_names=", ".join(failing_plans.mapped("name")),
                )
            )
        plan_tocheck = self.filtered(lambda plan: plan.res_model != "hr.employee")
        failing_templates = plan_tocheck.template_ids.filtered(
            lambda tpl: tpl.responsible_type in {"coach", "manager", "employee"}
        )
        if failing_templates:
            raise UserError(
                self.env._(
                    "Plan activities %(template_names)s cannot use coach, manager or employee responsible as it is used only for employee plans.",
                    template_names=", ".join(
                        failing_templates.mapped("activity_type_id.name")
                    ),
                )
            )

    @api.model
    def _is_department_assignable(self, res_model):
        return res_model == "hr.employee"

    @api.depends("res_model")
    def _compute_department_assignable(self):
        for plan in self:
            plan.department_assignable = self._is_department_assignable(plan.res_model)

    @api.depends("res_model")
    def _compute_department_id(self):
        for plan in self.filtered(lambda plan: not plan.department_assignable):
            dbg.logic.debug(
                "[plan:%s] res_model %s not department-assignable, department "
                "%s cleared",
                plan.id,
                plan.res_model,
                plan.department_id.id,
            )
            plan.department_id = False
