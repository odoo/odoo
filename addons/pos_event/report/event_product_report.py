# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class EventProductReport(models.Model):
    """Event Registrations-based sales report, allowing to analyze sales and number of seats
    by event (type), ticket, etc. Each opened record will also give access to all this information."""
    _inherit = 'event.product.report'

    pos_order_id = fields.Many2one('pos.order', readonly=True)
    pos_order_line_id = fields.Many2one('pos.order.line', readonly=True)
    order_state = fields.Selection(selection_add=[
        ('pos_draft', 'New'),
        ('paid', 'Paid'),
        ('pos_done', 'Posted'),
        ('invoiced', 'Invoiced'),
    ])

    def _prepare_query(self):
        query = super()._prepare_query()
        query.append(self._pos_event_query())
        return query

    def _pos_event_query(self, with_=None, select=None, join=None, group_by=None):
        return '\n'.join([
            self._pos_event_with_clause(*(with_ or [])),
            self._pos_event_select_clause(*(select or [])),
            self._pos_event_from_clause(*(join or [])),
            self._pos_event_group_by_clause(*(group_by or []))
        ])

    def _pos_event_with_clause(self, *with_):
        # Extra clauses formatted as `cte1 AS (SELECT ...)`, `cte2 AS (SELECT ...)`...
        return """
            WITH """ + ',\n    '.join(with_) if with_ else ''

    def _pos_event_select_clause(self, *select):
        # Extra clauses formatted as `cte1.column1 AS new_column1`, `table1.column2 AS new_column2`...
        select_fields = """
            event_registration.pos_order_id AS pos_order_id,
            event_registration.pos_order_line_id AS pos_order_line_id,
            pos_order.date_order AS order_date,
            pos_order.partner_id AS partner_id,
            pos_order.user_id AS user_id,
            pos_order_line.product_id AS product_id,
            CASE 
                WHEN pos.state = 'draft' THEN 'pos_draft' 
                WHEN pos.state = 'done' THEN 'pos_done' 
                ELSE pos.state 
            END AS order_state,
            pos_order_line.price_subtotal_incl
                / CASE COALESCE(pos_order.currency_rate, 0) WHEN 0 THEN 1.0 ELSE pos_order.currency_rate END
                / pos_order_line.qty AS total,
            pos_order_line.price_subtotal
                / CASE COALESCE(pos_order.currency_rate, 0) WHEN 0 THEN 1.0 ELSE pos_order.currency_rate END
                / pos_order_line.qty AS total_untaxed,
            CASE
                WHEN pos_order_line.price_subtotal_incl = 0 THEN 'free'
                WHEN event_registration.is_paid THEN 'paid'
                ELSE 'to_pay'
            END payment_status"""
        return f'{self._prepare_select_clause()} \n {select_fields}' + (',\n' + ',\n'.join(select) if select else '')

    def _pos_event_from_clause(self, *join_):
        # Extra clauses formatted as `column1`, `column2`...
        from_fields = """
            LEFT JOIN pos_order ON pos_order.id = event_registration.pos_order_id
            LEFT JOIN pos_order_line ON sale_order_line.id = event_registration.pos_order_line_id"""
        return f'{self._prepare_from_clause()} \n {from_fields}' + ('\n'.join(join_) + '\n' if join_ else '')

    def _pos_event_group_by_clause(self, *group_by):
        # Extra clauses formatted like `column1`, `column2`...
        return """
            GROUP BY""" + ',\n    '.join(group_by) if group_by else ''
