# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Contacts(models.Model):
    _name = 'calendar.filters'
    _description = 'Calendar Filters'

    user_id = fields.Many2one('res.users', 'Me', required=True, default=lambda self: self.env.user, index=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', 'Employee', required=True, index=True)
    active = fields.Boolean('Active', default=True)
    partner_checked = fields.Boolean('Checked', default=True)  # used to know if the partner is checked in the filter of the calendar view for the user_id.
    filter_group = fields.Integer(compute='_compute_filter_group')

    _sql_constraints = [
        ('user_id_partner_id_unique', 'UNIQUE(user_id, partner_id)', 'A user cannot have the same contact twice.')
    ]

    @api.model
    def unlink_from_partner_id(self, partner_id):
        return self.search([('partner_id', '=', partner_id)]).unlink()

    @api.depends('partner_id')
    def _compute_filter_group(self):
        for cal_filter in self:
            # Is the filter for a partner linked to the filter user
            cal_filter.filter_group = 0 if cal_filter.user_id in cal_filter.partner_id.calendar_user_ids else 1
