# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class CalendarContacts(models.Model):
    _name = 'calendar.contacts'

    user_id = fields.Many2one('res.users', string='Me', default=lambda self: self.env.user)
    partner_id = fields.Many2one('res.partner', string='Employee', required=True)
    active = fields.Boolean(default=True)

    @api.model
    def unlink_from_partner_id(self, partner_id):
        self.search([('partner_id', '=', partner_id)]).unlink()
