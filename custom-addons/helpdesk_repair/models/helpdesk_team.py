# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class HelpdeskTeam(models.Model):
    _inherit = 'helpdesk.team'

    repairs_count = fields.Integer('Repairs Count', compute='_compute_repairs_count')

    def _compute_repairs_count(self):
        repair_data = self.env['repair.order'].sudo()._read_group([
            ('ticket_id', 'in', self.ticket_ids.ids),
            ('state', 'not in', ['done', 'cancel'])
        ], ['ticket_id'], ['__count'])
        mapped_data = {ticket.id: count for ticket, count in repair_data}
        for team in self:
            team.repairs_count = sum([val for key, val in mapped_data.items() if key in team.ticket_ids.ids])
