# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class EventEvent(models.Model):
    _inherit = 'event.event'

    sale_order_lines_ids = fields.One2many(
        'sale.order.line', 'event_id',
        groups='sales_team.group_sale_salesman',
        string='All sale order lines pointing to this event')
    sale_price_total = fields.Monetary(
        string='Sales (Tax Included)', compute='_compute_sale_price_total',
        groups='sales_team.group_sale_salesman')

    @api.depends('company_id.currency_id',
                 'sale_order_lines_ids.price_total', 'sale_order_lines_ids.currency_id',
                 'sale_order_lines_ids.company_id', 'sale_order_lines_ids.order_id.date_order')
    def _compute_sale_price_total(self):
        """ Takes only confirmed the sale.order.lines related to this event and converts amounts
        from the currency of the sale order to the currency of the event company.

        To avoid extra overhead, we use conversion rates as of 'today'.
        Meaning we have a number that can change over time, but using the conversion rates
        at the time of the related sale.order would mean thousands of extra requests as we would
        have to do one conversion per sale.order (and a sale.order is created every time
        we sell a single event ticket). """
        date_now = fields.Datetime.now()
        event_subtotals = self.env['sale.order.line']._read_group(
            [('event_id', 'in', self.ids), ('price_total', '!=', 0), ('state', '=', 'sale')],
            ['event_id', 'currency_id'],
            ['price_total:sum'],
        )
        event_subtotals_mapping = dict.fromkeys(self._origin, 0)
        for event, currency, sum_price_total in event_subtotals:
            event_subtotals_mapping[event] += event.currency_id._convert(
                sum_price_total,
                currency,
                event.company_id or self.env.company,
                date_now,
            )

        for event in self:
            event.sale_price_total = event_subtotals_mapping.get(event._origin, 0)

    def action_view_linked_orders(self):
        """ Redirects to only the confirmed orders linked to the current events """
        sale_order_action = self.env["ir.actions.actions"]._for_xml_id("sale.action_orders")
        sale_order_action.update({
            'domain': [('state', '=', 'sale'), ('order_line.event_id', 'in', self.ids)],
            'context': {'create': 0},
        })
        return sale_order_action
