# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from itertools import groupby
from operator import itemgetter
from functools import reduce
from collections import defaultdict

class Event(models.Model):
    _inherit = 'event.event'

    pos_order_lines_ids = fields.One2many(
        'pos.order.line', 'event_id',
        groups='point_of_sale.group_pos_user',
        string="All pos order lines pointing to this event")
    pos_price_subtotal = fields.Monetary(
        string="PoS sales (Tax Excluded)", compute='_compute_pos_price_subtotal',
        groups='point_of_sale.group_pos_user')

    @api.depends('company_id.currency_id',
                 'pos_order_lines_ids', 'pos_order_lines_ids.currency_id')
    def _compute_pos_price_subtotal(self):
        """ Takes all the pos.order.lines related to this event and converts amounts
        from the currency of the pos orders to the currency of the event company.

        To avoid extra overhead, we use conversion rates as of 'today'.
        Meaning we have a number that can change over time, but using the conversion rates
        at the time of the related pos.order would mean thousands of extra requests as we would
        have to do one conversion per pos.order"""
        date_now = fields.Datetime.now()
        subtotal_by_event = defaultdict(lambda: 0)
        if self.ids:
            keys = itemgetter('event_id', 'currency_id')
            order_lines = self.env['pos.order.line'].search_read(
                [('event_id', 'in', self.ids), ('price_subtotal', '!=', 0)],
                ['event_id', 'currency_id', 'price_subtotal'],
                load=False)

            event_subtotals = []
            currency_id_set = set()
            for k, g in groupby(sorted(order_lines, key=keys), key=keys):
                lines = list(g)
                event_id, currency_id = k
                event_subtotals.append({
                    'event_id': event_id,
                    'currency_id': currency_id,
                    'subtotal': reduce(lambda accumulator, line: accumulator + line['price_subtotal'], lines, 0)
                })
                currency_id_set.add(currency_id)

            event_data = {}
            for event in self:
                event_data[event.id] = {
                    'company_id': event.company_id,
                    'currency_id': event.currency_id,
                }

            currency_by_id = {currency.id: currency for currency in self.env['res.currency'].browse(currency_id_set)}

            for event_subtotal in event_subtotals:
                event_id = event_subtotal['event_id']
                currency_id = event_subtotal['currency_id']
                price = event_data[event_id]['currency_id']._convert(
                    event_subtotal['subtotal'],
                    currency_by_id[currency_id],
                    event_data[event_id]['company_id'],
                    date_now)

                subtotal_by_event[event_id] += price

        for event in self:
            event.pos_price_subtotal = subtotal_by_event[event.id]

    def action_view_linked_pos_orders(self):
        """ Redirects to the pos orders linked to the current events """
        action = self.env['ir.actions.actions']._for_xml_id('point_of_sale.action_pos_pos_form')
        action.update({
            'domain': [('lines.event_id', 'in', self.ids)],
        })
        return action
