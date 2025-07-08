from odoo import models, fields, api


class ProjectTaskTemplate(models.Model):
    _inherit = "project.task.template"

    allow_timesheets = fields.Boolean(
        "Allow timesheets",
        compute='_compute_allow_timesheets', search='_search_allow_timesheets',
        compute_sudo=True, readonly=True, export_string_translation=False)

    encode_uom_in_days = fields.Boolean(compute='_compute_encode_uom_in_days', default=lambda self: self._uom_in_days(), export_string_translation=False)
    display_name = fields.Char(help="""Use these keywords in the title to set new tasks:\n
        30h Allocate 30 hours to the task
        #tags Set tags on the task
        @user Assign the task to a user
        ! Set the task a medium priority
        !! Set the task a high priority
        !!! Set the task a urgent priority\n
        Make sure to use the right format and order e.g. Improve the configuration screen 5h #feature #v16 @Mitchell !""",
    )

    def _uom_in_days(self):
        return self.env.company.timesheet_encode_uom_id == self.env.ref('uom.product_uom_day')

    def _compute_encode_uom_in_days(self):
        self.encode_uom_in_days = self._uom_in_days()

    @api.depends('project_id.allow_timesheets')
    def _compute_allow_timesheets(self):
        for task in self:
            task.allow_timesheets = task.project_id.allow_timesheets

    def _search_allow_timesheets(self, operator, value):
        query = self.env['project.project'].sudo()._search([
            ('allow_timesheets', operator, value),
        ])
        return [('project_id', 'in', query)]
