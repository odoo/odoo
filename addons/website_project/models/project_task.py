# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class ProjectTask(models.Model):
    _inherit = 'project.task'

    # Need this field to check there is no email loops when Odoo reply automatically
    email_from = fields.Char('Email From')
    # Used to submit tasks from a contact form
    partner_name = fields.Char(string='Customer Name', related="partner_id.name", store=True, readonly=False, tracking=False)
    partner_phone = fields.Char(
        compute='_compute_partner_phone', inverse='_inverse_partner_phone',
        string="Contact Number", readonly=False, store=True, copy=False)
    partner_company_name = fields.Char(string='Company Name', related="partner_id.company_name", store=True, readonly=False, tracking=False)

    @api.depends('partner_id.phone', 'partner_id.mobile')
    def _compute_partner_phone(self):
        for task in self:
            task.partner_phone = task.partner_id.mobile or task.partner_id.phone or False

    def _inverse_partner_phone(self):
        for task in self:
            if task.partner_id:
                if task.partner_id.mobile or not task.partner_id.phone:
                    task.partner_id.mobile = task.partner_phone
                else:
                    task.partner_id.phone = task.partner_phone
