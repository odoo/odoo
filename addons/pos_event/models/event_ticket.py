# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models

class EventTicket(models.Model):
    _inherit = 'event.event.ticket'

    @api.model
    def get_updated_ticket_seats_available(self, tickets_id):
        ticket_ids = self.search_read(
            [('id', 'in', tickets_id)],
            ['seats_available'], load=False)
        return ticket_ids
