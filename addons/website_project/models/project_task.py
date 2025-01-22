from odoo import fields, models


class ProjectTask(models.Model):
    _inherit = 'project.task'

    # Used to submit tasks from a contact form
    partner_name = fields.Char(string='Customer Name', related="partner_id.name", store=True, readonly=False, tracking=False)
    partner_company_name = fields.Char(string='Company Name', related="partner_id.company_name", store=True, readonly=False, tracking=False)
