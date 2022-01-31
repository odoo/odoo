# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, tools


class EventSaleReport(models.Model):
    _name = 'event.sale.report'
    _description = 'Event Sales Report'
    _auto = False
    _rec_name = 'id'

    event_id = fields.Many2one('event.event', string='Event', readonly=True)
    event_ticket_ids = fields.Many2one('event.event.ticket', string='Event Ticket', readonly=True)
    sale_price_total = fields.Float('Total Revenues', readonly=True)
    sale_price_subtotal = fields.Float('Untaxed Total Revenues', readonly=True)
    seats_available = fields.Integer('Seats Available', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute('CREATE OR REPLACE VIEW %s AS (%s);' % (self._table, self._query()))

    def _query(self):
        return """
            %(with_clause)s
            %(select_clause)s
            FROM event_sale
            %(join_clause)s
            %(group_by_clause)s
        """ % {
            'with_clause': self._with_clause(),
            'select_clause': self._select_clause(),
            'join_clause': self._join_clause(),
            'group_by_clause': self._group_by_clause(),
        }

    def _with_clause(self):
        return """
            WITH event_sale AS (
                SELECT
                    sale_order_line.event_id as event_id,
                    sale_order_line.event_ticket_id as event_ticket_ids,
                    SUM(sale_order_line.price_total) / CASE COALESCE(sale_order.currency_rate, 0) WHEN 0 THEN 1.0 ELSE sale_order.currency_rate END as sale_price_total,
                    SUM(sale_order_line.price_subtotal) / CASE COALESCE(sale_order.currency_rate, 0) WHEN 0 THEN 1.0 ELSE sale_order.currency_rate END as sale_price_subtotal
                FROM sale_order_line
                LEFT JOIN sale_order ON sale_order.id = sale_order_line.order_id
                WHERE sale_order_line.event_id IS NOT NULL
                GROUP BY
                    sale_order_line.event_id,
                    sale_order_line.event_ticket_id,
                    sale_order.currency_rate
            )
        """

    def _select_clause(self):
        return """
            SELECT
                ROW_NUMBER() OVER (ORDER BY event_sale.event_id) as id,
                event_sale.event_id as event_id,
                event_sale.event_ticket_ids as event_ticket_ids,
                SUM(event_sale.sale_price_total) as sale_price_total,
                SUM(event_sale.sale_price_subtotal) as sale_price_subtotal,
                event_event_ticket.seats_available as seats_available
        """

    def _join_clause(self):
        return """
            LEFT JOIN event_event_ticket ON event_sale.event_ticket_ids = event_event_ticket.id
        """

    def _group_by_clause(self):
        return """
            GROUP BY
                event_sale.event_id,
                event_sale.event_ticket_ids,
                event_event_ticket.seats_available
        """

    def action_show_revenues(self):
        return self.env['ir.actions.act_window']._for_xml_id('event_sale.event_sale_report_action')
