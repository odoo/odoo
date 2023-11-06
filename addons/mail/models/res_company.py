# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, tools


class Company(models.Model):
    _name = 'res.company'
    _inherit = 'res.company'

    catchall_email = fields.Char(string="Catchall Email", compute="_compute_catchall")
    catchall_formatted = fields.Char(string="Catchall", compute="_compute_catchall")
    # the compute method is sudo'ed because it needs to access res.partner records
    # portal users cannot access those (but they should be able to read the company email address)
    email_formatted = fields.Char(string="Formatted Email",
        compute="_compute_email_formatted", compute_sudo=True)

    @api.depends('name')
    def _compute_catchall(self):
        ConfigParameter = self.env['ir.config_parameter'].sudo()
        alias = ConfigParameter.get_param('mail.catchall.alias')
        domain = ConfigParameter.get_param('mail.catchall.domain')
        if alias and domain:
            for company in self:
                company.catchall_email = '%s@%s' % (alias, domain)
                company.catchall_formatted = tools.formataddr((company.name, company.catchall_email))
        else:
            for company in self:
                company.catchall_email = ''
                company.catchall_formatted = ''

    @api.depends('partner_id.email_formatted', 'catchall_formatted')
    def _compute_email_formatted(self):
        for company in self:
            if company.partner_id.email_formatted:
                company.email_formatted = company.partner_id.email_formatted
            elif company.catchall_formatted:
                company.email_formatted = company.catchall_formatted
            else:
                company.email_formatted = ''
