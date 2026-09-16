from odoo import _, api, exceptions, fields, models


class MailActivityPlanTemplate(models.Model):
    _inherit = "mail.activity.plan.template"

    responsible_type = fields.Selection(
        selection_add=[("fleet_manager", "Fleet Manager")],
        ondelete={"fleet_manager": "set on_demand"},
    )

    @api.constrains("plan_id", "responsible_type")
    def _check_responsible_hr_fleet(self):
        for template in self.filtered(
            lambda tpl: tpl.plan_id.res_model != "hr.employee"
        ):
            if template.responsible_type == "fleet_manager":
                raise exceptions.ValidationError(
                    _("Fleet Manager is limited to Employee plans.")
                )

    def _get_responsible_and_complaints(self, on_demand_responsible, employee):
        if (
            self.responsible_type == "fleet_manager"
            and self.plan_id.res_model == "hr.employee"
        ):
            employee_id = self.env["hr.employee"].browse(employee._origin.id)
            vehicle = employee_id.car_ids[:1]
            error = False
            warning = False
            if not vehicle:
                error = _("Employee %s is not linked to a vehicle.", employee_id.name)
            manager = vehicle._get_manager_user()
            if vehicle and not manager:
                warning = _(
                    "The vehicle of employee %(employee)s is not linked to a fleet manager, assigning to you.",
                    employee=employee_id.name,
                )
            return {
                "responsible": manager or self.env.user,
                "error": error,
                "warning": warning,
            }
        return super()._get_responsible_and_complaints(on_demand_responsible, employee)
