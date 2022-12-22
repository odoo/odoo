# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from itertools import groupby
from odoo import api, models
from operator import itemgetter
from time import strftime

class EventTicket(models.Model):
    _inherit = 'event.event.ticket'

    @api.model
    def get_ticket_linked_to_product_available_pos(self):
        event_ids = self.env['event.event'].search(
            [('event_ticket_ids.product_id.available_in_pos', '=', True), ('date_end', '>=', strftime('%Y-%m-%d 00:00:00'))])
        event_ids = event_ids.filtered('event_registrations_started')   # computed field not searchable

        ticket_ids = self.search_read(
            [('event_id', 'in', event_ids.mapped('id')), ('product_id.available_in_pos', '=', True)],
            ['name', 'description', 'sale_available', 'event_id', 'product_id', 'seats_available'], load=False)
        res = []
        key = itemgetter('event_id')
        for k, g in groupby(sorted(ticket_ids, key=key), key=key):
            event = event_ids.filtered(lambda e: e.id == k).read(
                    ['name', 'event_registrations_open', 'date_begin', 'date_end', 'seats_available'])[0]
            event['tickets'] = list(g)
            res.append(event)

        return res


