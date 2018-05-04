# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class MailBlackList(models.Model):
    """ Model of blacklisted email addresses to stop sending emails."""
    _name = 'mail.blacklist'
    _description = 'Mail Blacklist'

    name = fields.Char(string='Name')
    email = fields.Char(string='Email Address', required=True)
    company_id = fields.Many2one('res.company', string='Company Name')
    _sql_constraints = [
        ('unique_email', 'unique (email)', 'Email address already exists!')
    ]

    @api.model
    def create(self, vals):
        partner_ids = self.env['res.partner'].search([('email', 'ilike', vals['email'])])
        partner_ids.message_post(body=_('The email address %s has been blacklisted.') % (vals['email'],))
        return super(MailBlackList, self).create(vals)
