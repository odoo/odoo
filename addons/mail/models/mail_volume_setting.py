# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MailVolumeSetting(models.Model):
    """ Represents the volume of the sound that the user of user_setting_id will receive from partner_id. """
    _name = 'mail.volume.setting'
    _description = 'Mail Volume Setting'

    user_setting_id = fields.Many2one('mail.user.settings', required=True, ondelete='cascade')

    partner_id = fields.Many2one('res.partner', required=True, ondelete='cascade')
    volume = fields.Float(default=1.0, help="Ranges between 0.0 and 1.0, scale depends on the browser implementation")

    _sql_constraints = [
        ('uniq_mail_user_setting_partner_id', 'unique(user_setting_id, partner_id)',
         'There can only be one setting per partner'),
    ]
