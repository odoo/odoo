from odoo import fields, models


class ProjectTimesheetHolidaysConfig(models.Model):
    _name = "project_timesheet_holidays.config"
    _description = "A company's project timesheet holidays configuration"
    _inherit = ["mixin.company.config"]

    leave_timesheet_task_id = fields.Many2one(
        comodel_name="project.task",
        string="Time Off Task",
        domain="[('project_id', '=', internal_project_id)]",
    )
