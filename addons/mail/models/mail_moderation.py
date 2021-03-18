# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Moderation(models.Model):
    _name = 'mail.moderation'
    _description = 'Channel black/white list'

    email = fields.Char(string="Email", index=True, required=True)
    status = fields.Selection([
        ('allow', 'Always Allow'),
        ('ban', 'Permanent Ban')],
        string="Status", required=True)
    channel_id = fields.Many2one('mail.channel', string="Channel", index=True, required=True)

    _sql_constraints = [
        ('channel_email_uniq', 'unique (email,channel_id)', 'The email address must be unique per channel !')
    ]
