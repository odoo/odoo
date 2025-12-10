# -*- coding: utf-8 -*-
import logging
from calendar import monthrange
from datetime import date as pydate

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class EmployeeTaskTemplate(models.Model):
    _name = "employee.task.template"
    _description = "Employee Task Template"
    _order = "name"

    name = fields.Char(required=True)
    description = fields.Text()
    frequency = fields.Selection(
        [
            ("daily", "Daily"),
            ("weekly", "Weekly"),
            ("monthly", "Monthly"),
        ],
        default="daily",
        required=True,
    )
    weekday = fields.Selection(
        [
            ("0", "Monday"),
            ("1", "Tuesday"),
            ("2", "Wednesday"),
            ("3", "Thursday"),
            ("4", "Friday"),
            ("5", "Saturday"),
            ("6", "Sunday"),
        ],
        string="Weekday",
        help="Day of week for weekly tasks.",
    )
    month_day = fields.Integer(string="Month Day", help="Day of month for monthly tasks.")
    employee_ids = fields.Many2many("hr.employee", string="Employees")
    company_id = fields.Many2one("res.company", string="Company", default=lambda self: self.env.company)
    active = fields.Boolean(default=True)


class EmployeeTask(models.Model):
    _name = "employee.task"
    _description = "Employee Task"
    _order = "date desc, id desc"

    name = fields.Char(required=True)
    employee_id = fields.Many2one("hr.employee", string="Employee", required=True)
    date = fields.Date(required=True)
    deadline = fields.Datetime()
    status = fields.Selection(
        [
            ("todo", "To Do"),
            ("done", "Done"),
            ("cancel", "Cancelled"),
        ],
        default="todo",
        required=True,
    )
    template_id = fields.Many2one("employee.task.template", string="Template", readonly=True)
    company_id = fields.Many2one("res.company", string="Company", default=lambda self: self.env.company)
    board_post_id = fields.Many2one("employee.board.post", string="Related Board Post")
    note = fields.Text()

    def action_mark_done(self):
        for task in self:
            task.status = "done"
        return True

    def cron_generate_tasks(self):
        """Generate tasks from active templates.

        - daily: every day
        - weekly: only when weekday matches template.weekday
        - monthly: only when day-of-month matches template.month_day
        Skip if a task for same template/employee/date already exists.
        """
        today = fields.Date.context_today(self)
        weekday = str(pydate.fromisoformat(str(today)).weekday())
        today_dt = pydate.fromisoformat(str(today))
        year, month, day = today_dt.year, today_dt.month, today_dt.day

        templates = (
            self.env["employee.task.template"]
            .sudo()
            .search([("active", "=", True)])
        )
        for template in templates:
            if not template.employee_ids:
                _logger.warning(
                    "Employee Task Template '%s' has no employees assigned; skipping.",
                    template.display_name,
                )
                continue

            if template.frequency == "weekly" and template.weekday and template.weekday != weekday:
                continue
            if template.frequency == "monthly" and template.month_day:
                month_day = int(template.month_day or 0)
                if month_day <= 0:
                    _logger.warning(
                        "Employee Task Template '%s' has invalid month_day=%s; skipping.",
                        template.display_name,
                        template.month_day,
                    )
                    continue
                last_day = monthrange(year, month)[1]
                target_day = min(month_day, last_day)
                if target_day != day:
                    continue

            for employee in template.employee_ids:
                domain = [
                    ("template_id", "=", template.id),
                    ("employee_id", "=", employee.id),
                    ("date", "=", today),
                ]
                exists = self.sudo().search_count(domain)
                if exists:
                    continue
                self.sudo().create(
                    {
                        "name": template.name,
                        "employee_id": employee.id,
                        "date": today,
                        "status": "todo",
                        "template_id": template.id,
                        "company_id": template.company_id.id or employee.company_id.id,
                    }
                )
