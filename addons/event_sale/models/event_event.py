# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Event(models.Model):
    _inherit = 'event.event'

    sale_order_lines_ids = fields.One2many(
        'sale.order.line', 'event_id',
        groups='sales_team.group_sale_salesman',
        string='All sale order lines pointing to this event')
    sale_price_subtotal = fields.Monetary(
        string='Sales (Tax Excluded)', compute='_compute_sale_price_subtotal',
        groups='sales_team.group_sale_salesman')
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        related='company_id.currency_id', readonly=True)

    @api.depends('company_id.currency_id',
                 'sale_order_lines_ids.price_subtotal', 'sale_order_lines_ids.currency_id',
                 'sale_order_lines_ids.company_id', 'sale_order_lines_ids.order_id.date_order')
    def _compute_sale_price_subtotal(self):
        """ Takes all the sale.order.lines related to this event and converts amounts
        from the currency of the sale order to the currency of the event company.

        To avoid extra overhead, we use conversion rates as of 'today'.
        Meaning we have a number that can change over time, but using the conversion rates
        at the time of the related sale.order would mean thousands of extra requests as we would
        have to do one conversion per sale.order (and a sale.order is created every time
        we sell a single event ticket). """
        date_now = fields.Datetime.now()
        sale_price_by_event = {}
        if self.ids:
            event_subtotals = self.env['sale.order.line']._read_group(
                [('event_id', 'in', self.ids),
                 ('price_subtotal', '!=', 0),
                 ('state', '!=', 'cancel')],
                ['event_id', 'currency_id', 'price_subtotal:sum'],
                ['event_id', 'currency_id'],
                lazy=False
            )

            company_by_event = {
                event._origin.id or event.id: event.company_id
                for event in self
            }

            currency_by_event = {
                event._origin.id or event.id: event.currency_id
                for event in self
            }

            currency_by_id = {
                currency.id: currency
                for currency in self.env['res.currency'].browse(
                    [event_subtotal['currency_id'][0] for event_subtotal in event_subtotals]
                )
            }

            for event_subtotal in event_subtotals:
                price_subtotal = event_subtotal['price_subtotal']
                event_id = event_subtotal['event_id'][0]
                currency_id = event_subtotal['currency_id'][0]
                sale_price = currency_by_event[event_id]._convert(
                    price_subtotal,
                    currency_by_id[currency_id],
                    company_by_event[event_id] or self.env.company,
                    date_now)
                if event_id in sale_price_by_event:
                    sale_price_by_event[event_id] += sale_price
                else:
                    sale_price_by_event[event_id] = sale_price

        for event in self:
            event.sale_price_subtotal = sale_price_by_event.get(event._origin.id or event.id, 0)

    def action_view_linked_orders(self):
        """ Redirects to the orders linked to the current events """
        sale_order_action = self.env["ir.actions.actions"]._for_xml_id("sale.action_orders")
        sale_order_action.update({
            'domain': [('state', '!=', 'cancel'), ('order_line.event_id', 'in', self.ids)],
            'context': {'create': 0},
        })
        return sale_order_action
