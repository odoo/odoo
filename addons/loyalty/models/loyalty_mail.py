# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

# Allow promo programs to send mails upon certain triggers
# Like : 'At creation' and 'When reaching X points'

class LoyaltyMail(models.Model):
    _name = 'loyalty.mail'
    _description = 'Loyalty Communication'

    active = fields.Boolean(default=True)
    program_id = fields.Many2one('loyalty.program', required=True, ondelete='cascade')
    trigger = fields.Selection([
        ('create', 'At Creation'),
        ('points_reach', 'When Reaching')], string='When', required=True
    )
    points = fields.Float()
    mail_template_id = fields.Many2one('mail.template', string="Email Template", required=True, domain=[('model', '=', 'loyalty.card')])
