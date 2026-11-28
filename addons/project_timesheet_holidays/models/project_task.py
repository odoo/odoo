# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.fields import Domain


class ProjectTask(models.Model):
    _inherit = 'project.task'

    is_timeoff_task = fields.Boolean("Is Time off Task", compute="_compute_is_timeoff_task", search="_search_is_timeoff_task", export_string_translation=False, groups="hr_timesheet.group_hr_timesheet_user")

    @api.depends_context('allowed_company_ids')
    def _compute_is_timeoff_task(self):
        timeoff_tasks = self & self.env.companies.leave_timesheet_task_id
        timeoff_tasks.is_timeoff_task = True
        (self - timeoff_tasks).is_timeoff_task = False

    def _search_is_timeoff_task(self, operator, value):
        if operator != 'in':
            return NotImplemented

        return Domain('id', 'in', self.env.companies.leave_timesheet_task_id.ids)
