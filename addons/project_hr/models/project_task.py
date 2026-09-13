from odoo import api, fields, models
from odoo.tools import LazyTranslate

_lt = LazyTranslate(__name__)


class ProjectTask(models.Model):
    _name = "project.task"
    _inherit = ["mixin.hr", "project.task"]

    employee_ids = fields.Many2many(
        comodel_name="hr.employee",
        relation="project_task_employee_rel",
        column1="task_id",
        column2="employee_id",
        string="Assignees",
        default=lambda self: self._default_employee_ids(),
        falsy_value_label=_lt("👤 Unassigned"),
        tracking=True,
    )

    user_ids = fields.Many2many(
        comodel_name="res.users",
        relation="project_task_user_rel",
        column1="task_id",
        column2="user_id",
        string="Assignees (Users)",
        compute="_compute_user_ids",
        default=None,
        store=True,
        readonly=True,
        tracking=False,
    )

    @api.model
    def _default_employee_ids(self):
        if any(
            key in self.env.context
            for key in (
                "default_triage_ids",
                "default_triage_id",
            )
        ):
            return self.env["hr.employee"].search(
                [
                    ("user_id", "=", self.env.uid),
                    ("company_id", "=", self.env.company.id),
                ],
                limit=1,
            )
        return self.env["hr.employee"]

    @api.depends("employee_ids.user_id")
    def _compute_user_ids(self):
        for task in self:
            task.user_ids = task.employee_ids.user_id

    @api.model_create_multi
    def create(self, vals_list):
        tasks = super().create(vals_list)
        now = fields.Datetime.now()
        for task in tasks:
            if task.employee_ids and not task.date_assign:
                task.sudo().date_assign = now
        return tasks

    def _prepare_reservation_vals_list(self):
        self.check_singleton()
        start_field, end_field = self._get_fields_reservation_date()
        if not start_field or not end_field:
            return []
        date_start = self[start_field]
        date_end = self[end_field]
        if not date_start or not date_end:
            return []

        vals_list = []
        for employee in self.employee_ids:
            resource = employee.resource_id
            if not resource:
                continue
            vals_list.append(
                {
                    "name": self.display_name,
                    "date_start": date_start,
                    "date_end": date_end,
                    "resource_id": resource.id,
                    "allocated_percentage": self.allocated_percentage or 100.0,
                    "enforcement_mode": "soft",
                }
            )
        return vals_list

    def _get_fields_sync_trigger(self):
        triggers = super()._get_fields_sync_trigger()
        triggers.discard("user_ids")
        triggers.add("employee_ids")
        return triggers

    def action_view_schedule(self):
        self.check_singleton()
        resources = self.employee_ids.resource_id

        if len(resources) == 1:
            action_name = self.env._("Schedule — %s", resources.name)
        elif resources:
            action_name = self.env._("Schedule — %s assignees", len(resources))
        else:
            action_name = self.env._("Schedule")

        context = {"search_default_my_schedule": 0}
        start_field, end_field = self._get_fields_reservation_date()
        anchor = (start_field and self[start_field]) or (end_field and self[end_field])
        if anchor:
            context["initial_date"] = anchor

        return {
            "type": "ir.actions.act_window",
            "name": action_name,
            "res_model": "resource.reservation",
            "view_mode": "calendar,list,form",
            "domain": [("resource_id", "in", resources.ids)],
            "context": context,
        }

    def write(self, vals):
        now = fields.Datetime.now()
        task_ids_without_employee: set[int] = set()
        if "employee_ids" in vals and "date_assign" not in vals:
            task_ids_without_employee = {
                task.id for task in self if not task.employee_ids
            }

        result = super().write(vals)

        if "employee_ids" in vals:
            self._create_missing_triages()
            for task in self.sudo():
                if not task.employee_ids and task.date_assign:
                    task.date_assign = False
                elif task.id in task_ids_without_employee:
                    task.date_assign = now

        return result
