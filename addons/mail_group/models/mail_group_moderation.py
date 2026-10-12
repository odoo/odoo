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
    mail_group_id = fields.Many2one('mail.group', string='Group', required=True, index=True, ondelete='cascade')

    _mail_group_email_uniq = models.Constraint(
        'UNIQUE(mail_group_id, email)',
        'You can create only one rule for a given email address in a group.',
    )

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            email_normalized = email_normalize(values.get('email'))
            if not email_normalized:
                raise UserError(_('Invalid email address “%s”', values.get('email')))
            values['email'] = email_normalized
        return super().create(vals_list)

    def write(self, vals):
        if 'email' in vals:
            email_normalized = email_normalize(vals['email'])
            if not email_normalized:
                raise UserError(_('Invalid email address “%s”', vals.get('email')))
            vals['email'] = email_normalized
        return super().write(vals)
