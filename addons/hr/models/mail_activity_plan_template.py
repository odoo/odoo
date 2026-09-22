from odoo import api, fields, models
from odoo.exceptions import ValidationError

from ..tools import debug_log as dbg


class MailActivityPlanTemplate(models.Model):
    _inherit = "mail.activity.plan.template"

    responsible_type = fields.Selection(
        selection_add=[
            ("coach", "Coach"),
            ("manager", "Manager"),
            ("employee", "Employee"),
        ],
        ondelete={"coach": "cascade", "manager": "cascade", "employee": "cascade"},
    )

    @api.constrains("plan_id", "responsible_type")
    def _check_responsible_hr(self):
        for template in self.filtered(
            lambda tpl: tpl.plan_id.res_model != "hr.employee"
        ):
            if template.responsible_type in {"coach", "manager", "employee"}:
                raise ValidationError(
                    self.env._("Those responsible types are limited to Employee plans.")
                )

    def _get_responsible_result_from_parents(
        self, employee, responsible, error_message
    ):
        responsible_parent = responsible
        viewed_responsible = [employee]
        while True:
            dbg.logic.debug(
                "[employee:%s] responsible walk: at %s, user=%s, seen %d",
                employee.id,
                responsible_parent.id,
                responsible_parent.user_id.id,
                len(viewed_responsible),
            )
            if not responsible_parent:
                return {
                    "error": False,
                    "responsible": self.env.user,
                    "warning": error_message,
                }
            if responsible_parent.user_id:
                return {
                    "error": False,
                    "responsible": responsible_parent.user_id,
                    "warning": False,
                }
            if responsible_parent in viewed_responsible:
                return {
                    "error": self.env._(
                        "Oops! It seems there is a problem with your team structure.\
                        We found a circular reporting loop and no one in that loop is linked to a user.\
                        Please double-check that everyone reports to the correct manager."
                    ),
                    "warning": False,
                    "responsible": False,
                }
            else:
                viewed_responsible.append(responsible_parent)
                responsible_parent = responsible_parent.parent_id

    def _get_responsible_and_complaints(self, on_demand_responsible, employee):
        if self.plan_id.res_model != "hr.employee" or self.responsible_type not in {
            "coach",
            "manager",
            "employee",
        }:
            return super()._get_responsible_and_complaints(
                on_demand_responsible, employee
            )
        result = {"error": "", "warning": "", "responsible": False}
        dbg.logic.debug(
            "[template:%s] responsible_type=%s for employee %s (coach=%s manager=%s "
            "user=%s)",
            self.id,
            self.responsible_type,
            employee.id,
            employee.coach_id.id,
            employee.parent_id.id,
            employee.user_id.id,
        )
        if self.responsible_type == "coach":
            result["responsible"] = employee.coach_id.user_id
            if not result["responsible"]:
                # No usable coach: walk up from the coach's manager until
                # somebody has a user, and fall back to whoever is launching the
                # plan if nobody does. A missing coach starts that walk from
                # nothing and lands on the same fallback -- an employee still
                # being onboarded is precisely who these plans are for, and
                # refusing to launch at all is worse than saying who it went to.
                result = self._get_responsible_result_from_parents(
                    employee=employee,
                    responsible=employee.coach_id.parent_id,
                    error_message=(
                        self.env._("The user of %s's coach is not set.", employee.name)
                        if employee.coach_id
                        else self.env._(
                            "Coach of employee %s is not set.", employee.name
                        )
                    ),
                )

        elif self.responsible_type == "manager":
            result["responsible"] = employee.parent_id.user_id
            if not result["responsible"]:
                # Same walk as above, one level up: from the manager's manager,
                # and from nothing when there is no manager yet.
                result = self._get_responsible_result_from_parents(
                    employee=employee,
                    responsible=employee.parent_id.parent_id,
                    error_message=(
                        self.env._(
                            "The manager of %s should be linked to a user.",
                            employee.name,
                        )
                        if employee.parent_id
                        else self.env._(
                            "Manager of employee %s is not set.", employee.name
                        )
                    ),
                )

        elif self.responsible_type == "employee":
            result["responsible"] = employee.user_id
            if not result["responsible"]:
                result = self._get_responsible_result_from_parents(
                    employee=employee,
                    responsible=employee.parent_id,
                    error_message=self.env._(
                        "The employee %s should be linked to a user.", employee.name
                    ),
                )

        dbg.logic.debug(
            "[template:%s] responsible for employee %s -> user %s (error=%s "
            "warning=%s)",
            self.id,
            employee.id,
            result["responsible"] and result["responsible"].id,
            bool(result["error"]),
            bool(result["warning"]),
        )
        return result
