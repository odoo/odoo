# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class EventProductReport(models.Model):
    """Event Registrations-based sales report, allowing to analyze sales and number of seats
    by event (type), ticket, etc. Each opened record will also give access to all this information."""
    _name = 'event.product.report'
    _description = 'Event Product Report'
    _auto = False
    _rec_name = 'event_registration_id'
    _order = 'order_date'

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
    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True)
    user_id = fields.Many2one('res.users', string='Salesperson', readonly=True)
    order_state = fields.Selection([], default='fdp', string="Order Status", readonly=True)
    order_date = fields.Datetime(string="Order Date", readonly=True)
    total = fields.Float(string="Revenues", readonly=True)
    total_untaxed = fields.Float(string="Untaxed Revenues", readonly=True)
    is_paid = fields.Boolean('Is Paid', readonly=True)
    payment_status = fields.Selection(string="Payment Status", selection=[
        ('to_pay', 'Not Paid'),
        ('paid', 'Paid'),
        ('free', 'Free'),
    ])
    company_id = fields.Many2one('res.company', string='Company', readonly=True)

    @property
    def _table_query(self):
        return self._query()

    def _prepare_query(self):
        return []

    def _query(self):
        return '\n UNION ALL \n'.join(self._prepare_query())

    def _prepare_select_clause(self):
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
            event_registration.is_paid AS is_paid,
        
            event_event.event_type_id AS event_type_id,
            event_event.date_begin AS event_date_begin,
            event_event.date_end AS event_date_end,
        
            event_event_ticket.price AS event_ticket_price,"""

    def _prepare_from_clause(self):
        return """
            FROM event_registration
            LEFT JOIN event_event ON event_event.id = event_registration.event_id
            LEFT JOIN event_event_ticket ON event_event_ticket.id = event_registration.event_ticket_id"""
