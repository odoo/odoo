# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, tools


class EventSaleReport(models.Model):
    """Event Registrations-based sales report, allowing to analyze sales and number of seats
    by event (type), ticket, etc. Each opened record will also give access to all this information."""
    _name = 'event.sale.report'
    _description = 'Event Sales Report'
    _auto = False
    _rec_name = 'sale_order_line_id'

    event_type_id = fields.Many2one('event.type', string='Event Type', readonly=True)
    event_id = fields.Many2one('event.event', string='Event', readonly=True)
    event_date_begin = fields.Date(string='Event Start Date', readonly=True)
    event_date_end = fields.Date(string='Event End Date', readonly=True)
    event_ticket_id = fields.Many2one('event.event.ticket', string='Event Ticket', readonly=True)
    event_ticket_price = fields.Float(string='Ticket price', readonly=True)
    event_registration_create_date = fields.Date(string='Registration Date', readonly=True)
    event_registration_state = fields.Selection([
        ('draft', 'Unconfirmed'), ('cancel', 'Cancelled'),
        ('open', 'Confirmed'), ('done', 'Attended')],
        string='Registration Status', readonly=True)
    active = fields.Boolean('Is registration active (not archived)?')
    event_registration_id = fields.Many2one('event.registration', readonly=True)
    event_registration_name = fields.Char('Attendee Name', readonly=True)

    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    sale_order_id = fields.Many2one('sale.order', readonly=True)
    sale_order_date = fields.Datetime('Order Date', readonly=True)
    sale_order_partner_id = fields.Many2one('res.partner', string='Customer', readonly=True)
    sale_order_state = fields.Selection([
        ('draft', 'Quotation'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sales Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
        ], string='Sale Order Status', readonly=True)
    sale_order_user_id = fields.Many2one('res.users', string='Salesperson', readonly=True)
    sale_order_line_id = fields.Many2one('sale.order.line', readonly=True)
    sale_price = fields.Float('Revenues', readonly=True)
    sale_price_untaxed = fields.Float('Untaxed Revenues', readonly=True)
    invoice_partner_id = fields.Many2one('res.partner', string='Invoice Address', readonly=True)
    is_paid = fields.Boolean('Is Paid', readonly=True)
    payment_status = fields.Selection(string="Payment Status", selection=[
            ('to_pay', 'Not Paid'),
            ('paid', 'Paid'),
            ('free', 'Free'),
        ])
    company_id = fields.Many2one('res.company', string='Company', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute('CREATE OR REPLACE VIEW %s AS (%s);' % (self._table, self._query()))

    def _query(self, with_=None, select=None, join=None, group_by=None):
        return "\n".join([
            self._with_clause(*(with_ or [])),
            self._select_clause(*(select or [])),
            self._from_clause(*(join or [])),
            self._group_by_clause(*(group_by or []))
        ])

    def _with_clause(self, *with_):
        # Extra clauses formatted as `cte1 AS (SELECT ...)`, `cte2 AS (SELECT ...)`...
        return """
WITH 
    """ + ',\n    '.join(with_) if with_ else ''

    def _select_clause(self, *select):
        # Extra clauses formatted as `cte1.column1 AS new_column1`, `table1.column2 AS new_column2`...
        return """
SELECT
    ROW_NUMBER() OVER (ORDER BY event_registration.id) AS id,
    
    event_registration.id AS event_registration_id,
    event_registration.company_id AS company_id,
    event_registration.event_id AS event_id,
    event_registration.event_ticket_id AS event_ticket_id,
    event_registration.create_date AS event_registration_create_date,
    event_registration.name AS event_registration_name,
    event_registration.state AS event_registration_state, 
    event_registration.active AS active,
    event_registration.sale_order_id AS sale_order_id,
    event_registration.sale_order_line_id AS sale_order_line_id,
    event_registration.is_paid AS is_paid,
    
    event_event.event_type_id AS event_type_id,
    event_event.date_begin AS event_date_begin,
    event_event.date_end AS event_date_end,

    event_event_ticket.price AS event_ticket_price,

    sale_order.date_order AS sale_order_date,
    sale_order.partner_invoice_id AS invoice_partner_id,
    sale_order.partner_id AS sale_order_partner_id,
    sale_order.state AS sale_order_state,
    sale_order.user_id AS sale_order_user_id,
    
    sale_order_line.product_id AS product_id,
    sale_order_line.price_total
        / CASE COALESCE(sale_order.currency_rate, 0) WHEN 0 THEN 1.0 ELSE sale_order.currency_rate END
        / sale_order_line.product_uom_qty AS sale_price,
    sale_order_line.price_subtotal
        / CASE COALESCE(sale_order.currency_rate, 0) WHEN 0 THEN 1.0 ELSE sale_order.currency_rate END
        / sale_order_line.product_uom_qty AS sale_price_untaxed,
    CASE
        WHEN sale_order_line.price_total = 0 THEN 'free'
        WHEN event_registration.is_paid THEN 'paid'
        ELSE 'to_pay'
    END payment_status""" + (',\n    ' + ',\n    '.join(select) if select else '')

    def _from_clause(self, *join_):
        # Extra clauses formatted as `column1`, `column2`...
        return """
FROM event_registration
LEFT JOIN event_event ON event_event.id = event_registration.event_id
LEFT JOIN event_event_ticket ON event_event_ticket.id = event_registration.event_ticket_id
LEFT JOIN sale_order ON sale_order.id = event_registration.sale_order_id
LEFT JOIN sale_order_line ON sale_order_line.id = event_registration.sale_order_line_id
""" + ('\n'.join(join_) + '\n' if join_ else '')

    def _group_by_clause(self, *group_by):
        # Extra clauses formatted like `column1`, `column2`...
        return """
GROUP BY
    """ + ',\n    '.join(group_by) if group_by else ''
