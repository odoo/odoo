# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, tools


class Company(models.Model):
    _name = 'res.company'
    _inherit = 'res.company'

    def _default_alias_domain_id(self):
        return self.env['mail.alias.domain'].search([], limit=1)

    alias_domain_id = fields.Many2one(
        'mail.alias.domain', string='Email Domain',
        default=lambda self: self._default_alias_domain_id())
    alias_domain_name = fields.Char('Alias Domain Name', related='alias_domain_id.name', readonly=True, store=True)
    bounce_email = fields.Char(string="Bounce Email", compute="_compute_bounce")
    bounce_formatted = fields.Char(string="Bounce", compute="_compute_bounce")
    catchall_email = fields.Char(string="Catchall Email", compute="_compute_catchall")
    catchall_formatted = fields.Char(string="Catchall", compute="_compute_catchall")
    default_from_email = fields.Char(
        string="Default From", related="alias_domain_id.default_from_email",
        readonly=True)
    # the compute method is sudo'ed because it needs to access res.partner records
    # portal users cannot access those (but they should be able to read the company email address)
    email_formatted = fields.Char(
        string="Formatted Email",
        compute="_compute_email_formatted", compute_sudo=True)
    email_primary_color = fields.Char(
        "Email Header Color", compute="_compute_email_primary_color",
        readonly=False, store=True)
    email_secondary_color = fields.Char(
        "Email Button Color", compute="_compute_email_secondary_color",
        readonly=False, store=True)

    @api.depends('alias_domain_id', 'name')
    def _compute_bounce(self):
        self.bounce_email = ''
        self.bounce_formatted = ''

        for company in self.filtered('alias_domain_id'):
            bounce_email = company.alias_domain_id.bounce_email
            company.bounce_email = bounce_email
            company.bounce_formatted = tools.formataddr((company.name, bounce_email))

    @api.depends('alias_domain_id', 'name')
    def _compute_catchall(self):
        self.catchall_email = ''
        self.catchall_formatted = ''

        for company in self.filtered('alias_domain_id'):
            catchall_email = company.alias_domain_id.catchall_email
            company.catchall_email = catchall_email
            company.catchall_formatted = tools.formataddr((company.name, catchall_email))

    @api.depends('partner_id', 'catchall_formatted')
    def _compute_email_formatted(self):
        for company in self:
            if company.partner_id.email_formatted:
                company.email_formatted = company.partner_id.email_formatted
            elif company.catchall_formatted:
                company.email_formatted = company.catchall_formatted
            else:
                company.email_formatted = ''

    @api.depends('primary_color')
    def _compute_email_primary_color(self):
        """ When updating documents layout colors, force usage of same colors
        for emails as it is considered as base colors for all communication.
        Inverse is not true, people may change email colors without changing
        their overall layout. """
        for company in self:
            company.email_primary_color = company.primary_color or '#000000'

    @api.depends('secondary_color')
    def _compute_email_secondary_color(self):
        """ When updating documents layout colors, force usage of same colors
        for emails as it is considered as base colors for all communication.
        Inverse is not true, people may change email colors without changing
        their overall layout. """
        for company in self:
            company.email_secondary_color = company.secondary_color or '#875A7B'
