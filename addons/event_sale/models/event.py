# -*- coding: utf-8 -*-

from openerp import api, fields, models, _
from openerp.exceptions import UserError
import openerp.addons.decimal_precision as dp


class Event(models.Model):
    _inherit = 'event.event'

    def _default_tickets(self):
        try:
            product = self.env.ref('event_sale.product_product_event')
            return [{
                'name': _('Subscription'),
                'product_id': product.id,
                'price': 0,
            }]
        except ValueError:
            return self.env['event.event.ticket']

    event_ticket_ids = fields.One2many(
        'event.event.ticket', 'event_id', string='Event Ticket',
        default=_default_tickets, copy=True)

    badge_back = fields.Html(translate=True, states={'done': [('readonly', True)]})
    badge_innerleft = fields.Html('Badge Innner Left', translate=True, states={'done': [('readonly', True)]})
    badge_innerright = fields.Html('Badge Inner Right', translate=True, states={'done': [('readonly', True)]})


class EventTicket(models.Model):
    _name = 'event.event.ticket'
    _description = 'Event Ticket'

    def _default_product_id(self):
        try:
            product = self.env.ref('event_sale.product_product_event')
            return product.id
        except ValueError:
            return False

    name = fields.Char(required=True, translate=True)
    event_id = fields.Many2one('event.event', string='Event', required=True, ondelete='cascade')
    product_id = fields.Many2one(
        'product.product', string='Product',
        required=True, domain=[("event_type_id", "!=", False)],
        default=_default_product_id)
    registration_ids = fields.One2many('event.registration', 'event_ticket_id', string='Registrations')
    price = fields.Float(digits=dp.get_precision('Product Price'))
    deadline = fields.Date(string="Sales End")
    is_expired = fields.Boolean(compute='_is_expired')
    price_reduce = fields.Float(string="Price Reduce", compute="_compute_price_reduce",
                                digits=dp.get_precision('Product Price'))

    # seats fields
    seats_availability = fields.Selection(
        [('limited', 'Limited'), ('unlimited', 'Unlimited')],
        string='Available Seat', required=True, store=True, compute='_compute_seats', default="limited")
    seats_max = fields.Integer(string='Maximum Available Seats',
                               help="Define the number of available tickets. If you have too much registrations you will"
                                    "not BE able to sell tickets anymore. Set 0 to ignore this rule set as unlimited.")
    seats_reserved = fields.Integer(string='Reserved Seats', compute='_compute_seats', store=True)
    seats_available = fields.Integer(string='Available Seats', compute='_compute_seats', store=True)
    seats_unconfirmed = fields.Integer(string='Unconfirmed Seat Reservations', compute='_compute_seats', store=True)
    seats_used = fields.Integer(compute='_compute_seats', store=True)

    @api.one
    @api.depends('price', 'product_id.lst_price', 'product_id.price')
    def _compute_price_reduce(self):
        product = self.product_id
        discount = product.lst_price and (product.lst_price - product.price) / product.lst_price or 0.0
        self.price_reduce = (1.0 - discount) * self.price

    @api.one
    @api.depends('deadline')
    def _is_expired(self):
        if self.deadline:
            current_date = fields.Date.context_today(self.with_context({'tz': self.event_id.date_tz}))
            self.is_expired = self.deadline < current_date
        else:
            self.is_expired = False

    @api.depends('seats_max', 'registration_ids.state')
    def _compute_seats(self):
        """ Determine reserved, available, reserved but unconfirmed and used seats. """
        # initialize fields to 0 + compute seats availability
        for ticket in self:
            ticket.seats_availability = 'unlimited' if ticket.seats_max == 0 else 'limited'
            ticket.seats_unconfirmed = ticket.seats_reserved = ticket.seats_used = ticket.seats_available = 0
        # aggregate registrations by ticket and by state
        if self.ids:
            state_field = {
                'draft': 'seats_unconfirmed',
                'open': 'seats_reserved',
                'done': 'seats_used',
            }
            query = """ SELECT event_ticket_id, state, count(event_id)
                        FROM event_registration
                        WHERE event_ticket_id IN %s AND state IN ('draft', 'open', 'done')
                        GROUP BY event_ticket_id, state
                    """
            self.env.cr.execute(query, (tuple(self.ids),))
            for event_ticket_id, state, num in self.env.cr.fetchall():
                ticket = self.browse(event_ticket_id)
                ticket[state_field[state]] += num
        # compute seats_available
        for ticket in self:
            if ticket.seats_max > 0:
                ticket.seats_available = ticket.seats_max - (ticket.seats_reserved + ticket.seats_used)

    @api.one
    @api.constrains('registration_ids', 'seats_max')
    def _check_seats_limit(self):
        if self.seats_max and self.seats_available < 0:
            raise UserError(_('No more available seats for the ticket'))

    @api.onchange('product_id')
    def onchange_product_id(self):
        self.price = self.product_id.list_price or 0


class EventRegistration(models.Model):
    _inherit = 'event.registration'

    event_ticket_id = fields.Many2one('event.event.ticket', 'Event Ticket')
    # in addition to origin generic fields, add real relational fields to correctly
    # handle attendees linked to sale orders and their lines
    # TDE FIXME: maybe add an onchange on sale_order_id + origin
    sale_order_id = fields.Many2one('sale.order', 'Source Sale Order', ondelete='cascade')
    sale_order_line_id = fields.Many2one('sale.order.line', 'Sale Order Line', ondelete='cascade')

    @api.one
    @api.constrains('event_ticket_id', 'state')
    def _check_ticket_seats_limit(self):
        if self.event_ticket_id.seats_max and self.event_ticket_id.seats_available < 0:
            raise UserError(_('No more available seats for this ticket'))

    @api.model
    def create(self, vals):
        res = super(EventRegistration, self).create(vals)
        if res.origin or res.sale_order_id:
            message = _("The registration has been created for event %(event_name)s%(ticket)s from sale order %(order)s") % ({
                'event_name': '<i>%s</i>' % res.event_id.name,
                'ticket': res.event_ticket_id and _(' with ticket %s') % (('<i>%s</i>') % res.event_ticket_id.name) or '',
                'order': res.origin or res.sale_order_id.name})
            res.message_post(body=message)
        return res

    def _check_auto_confirmation(self):
        res = super(EventRegistration, self)._check_auto_confirmation()
        if res:
            if self.env['sale.order'].search([('state', '=', 'draft'), ('id', 'in', self.mapped('sale_order_id').ids)], limit=1):
                return False
        return res

    def _prepare_attendee_values(self, registration):
        """ Override to add sale related stuff """
        line_id = registration.get('sale_order_line_id')
        if line_id:
            registration.setdefault('partner_id', line_id.order_id.partner_id)
        att_data = super(EventRegistration, self)._prepare_attendee_values(registration)
        if line_id:
            att_data.update({
                'event_id': line_id.event_id.id,
                'event_id': line_id.event_id.id,
                'event_ticket_id': line_id.event_ticket_id.id,
                'origin': line_id.order_id.name,
                'sale_order_id': line_id.order_id.id,
                'sale_order_line_id': line_id.id,
            })
        return att_data
