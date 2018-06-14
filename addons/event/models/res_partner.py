# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class ResPartner(models.Model):
    _inherit = 'res.partner'

    event_count = fields.Integer("Events", compute='_compute_event_count', help="Number of events the partner has participated.")

    def _compute_event_count(self):
        if not self.user_has_groups('event.group_event_user'):
            return
        for partner in self:
            partner.event_count = self.env['event.event'].search_count([('registration_ids.partner_id', 'child_of', partner.ids)])

    @api.multi
    def action_event_view(self):
        action = self.env.ref('event.action_event_view').read()[0]
        action['context'] = {}
        action['domain'] = [('registration_ids.partner_id', 'child_of', self.ids)]
        return action
