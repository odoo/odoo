# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class CalendarContacts(models.Model):
    _name = 'calendar.contacts'

    user_id = fields.Many2one('res.users', string='Me', default=lambda self: self.env.user)
    partner_id = fields.Many2one('res.partner', string='Employee', required=True)
    active = fields.Boolean(default=True)
