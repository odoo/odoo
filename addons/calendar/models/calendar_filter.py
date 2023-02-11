# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Contacts(models.Model):
    _name = 'calendar.filters'
    _description = 'Calendar Filters'

    user_id = fields.Many2one('res.users', 'Me', required=True, default=lambda self: self.env.user)
    partner_id = fields.Many2one('res.partner', 'Employee', required=True)
    active = fields.Boolean('Active', default=True)
    partner_checked = fields.Boolean('Checked', default=True,
        help="This field is used to know if the partner is checked in the filter of the calendar view for the user_id.")

    _sql_constraints = [
        ('user_id_partner_id_unique', 'UNIQUE(user_id, partner_id)', 'A user cannot have the same contact twice.')
    ]

    @api.model
    def unlink_from_partner_id(self, partner_id):
        return self.search([('partner_id', '=', partner_id)]).unlink()
