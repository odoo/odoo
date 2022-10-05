# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class EventProductReport(models.Model):
    """Event Registrations-based sales report, allowing to analyze sales and number of seats
    by event (type), ticket, etc. Each opened record will also give access to all this information."""
    _inherit = 'event.product.report'

    sale_order_id = fields.Many2one('sale.order', readonly=True)
    order_state = fields.Selection(selection_add=[
        ('draft', 'Quotation'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sales Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled')])
    sale_order_line_id = fields.Many2one('sale.order.line', readonly=True)
    invoice_partner_id = fields.Many2one('res.partner', string='Invoice Address', readonly=True)

    def _prepare_query(self):
        query = super()._prepare_query()
        query.append(self._event_sale_query())
        return query

    def _event_sale_query(self, with_=None, select=None, join=None, group_by=None):
        return '\n'.join([
            self._event_sale_with_clause(*(with_ or [])),
            self._event_sale_select_clause(*(select or [])),
            self._event_sale_from_clause(*(join or [])),
            self._event_sale_group_by_clause(*(group_by or []))
        ])

    def _event_sale_with_clause(self, *with_):
        # Extra clauses formatted as `cte1 AS (SELECT ...)`, `cte2 AS (SELECT ...)`...
        return """
            WITH """ + ',\n    '.join(with_) if with_ else ''

    def _event_sale_select_clause(self, *select):
        # Extra clauses formatted as `cte1.column1 AS new_column1`, `table1.column2 AS new_column2`...
        select_fields = """
            event_registration.sale_order_id AS sale_order_id,
            event_registration.sale_order_line_id AS sale_order_line_id,
            sale_order.date_order AS order_date,
            sale_order.partner_invoice_id AS invoice_partner_id,
            sale_order.partner_id AS partner_id,
            sale_order.state AS order_state,
            sale_order.user_id AS user_id,

            sale_order_line.product_id AS product_id,
            CASE
                WHEN sale_order_line.product_uom_qty = 0 THEN 0
                ELSE
                sale_order_line.price_total
                    / CASE COALESCE(sale_order.currency_rate, 0) WHEN 0 THEN 1.0 ELSE sale_order.currency_rate END
                    / sale_order_line.product_uom_qty
            END AS total,
            CASE
                WHEN sale_order_line.product_uom_qty = 0 THEN 0
                ELSE
                sale_order_line.price_subtotal
                    / CASE COALESCE(sale_order.currency_rate, 0) WHEN 0 THEN 1.0 ELSE sale_order.currency_rate END
                    / sale_order_line.product_uom_qty
            END AS total_untaxed,
            CASE
                WHEN sale_order_line.price_total = 0 THEN 'free'
                WHEN event_registration.is_paid THEN 'paid'
                ELSE 'to_pay'
            END payment_status"""
        return f'{self._prepare_select_clause()} \n {select_fields}' + (',\n' + ',\n'.join(select) if select else '')

    def _event_sale_from_clause(self, *join_):
        # Extra clauses formatted as `column1`, `column2`...
        from_fields = """
            LEFT JOIN sale_order ON sale_order.id = event_registration.sale_order_id
            LEFT JOIN sale_order_line ON sale_order_line.id = event_registration.sale_order_line_id"""
        return f'{self._prepare_from_clause()} \n {from_fields}' + ('\n'.join(join_) + '\n' if join_ else '')

    def _event_sale_group_by_clause(self, *group_by):
        # Extra clauses formatted like `column1`, `column2`...
        return """
            GROUP BY""" + ',\n    '.join(group_by) if group_by else ''
