# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class ProjectTask(models.Model):
    _inherit = 'project.task'

    # Need this field to check there is no email loops when Odoo reply automatically
    email_from = fields.Char('Email From')
    # Used to submit tasks from a contact form
    partner_name = fields.Char(string='Customer Name', related="partner_id.name", store=True, readonly=False, tracking=False)
    partner_company_name = fields.Char(string='Company Name', related="partner_id.company_name", store=True, readonly=False, tracking=False)
