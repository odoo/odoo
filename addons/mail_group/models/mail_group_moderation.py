# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.tools import email_normalize


class MailGroupModeration(models.Model):
    """Represent the moderation rules for an email address in a group."""
    _name = 'mail.group.moderation'
    _description = 'Mailing List black/white list'

    email = fields.Char(string='Email', required=True)
    status = fields.Selection(
        [('allow', 'Always Allow'), ('ban', 'Permanent Ban')],
        string='Status', required=True, default='ban')
    mail_group_id = fields.Many2one('mail.group', string='Group', required=True, ondelete='cascade')

    _sql_constraints = [(
        'mail_group_email_uniq',
        'UNIQUE(mail_group_id, email)',
        'You can create only one rule for a given email address in a group.',
    )]

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            email_normalized = email_normalize(values.get('email'))
            if not email_normalized:
                raise UserError(_('Invalid email address “%s”', values.get('email')))
            values['email'] = email_normalized
        return super(MailGroupModeration, self).create(vals_list)

    def write(self, values):
        if 'email' in values:
            email_normalized = email_normalize(values['email'])
            if not email_normalized:
                raise UserError(_('Invalid email address “%s”', values.get('email')))
            values['email'] = email_normalized
        return super(MailGroupModeration, self).write(values)
