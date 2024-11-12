# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ProjectTask(models.Model):
    _inherit = 'project.task'

    # Need this field to check there is no email loops when Odoo reply automatically
    email_from = fields.Char('Email From')
    # Used to submit tasks from a contact form
    partner_name = fields.Char(string='Customer Name', related="partner_id.name", store=True, readonly=False)
    partner_phone = fields.Char(string='Customer Phone', related="partner_id.phone", store=True, readonly=False)
    partner_company_name = fields.Char(string='Company Name', related="partner_id.company_name", store=True, readonly=False)
