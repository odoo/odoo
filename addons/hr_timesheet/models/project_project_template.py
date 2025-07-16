from odoo import models, fields


class ProjectProjectTemplate(models.Model):
    _inherit = "project.project.template"

    allow_timesheets = fields.Boolean("Timesheets", readonly=False, default=True)
    allocated_hours = fields.Float(string='Allocated Time')
