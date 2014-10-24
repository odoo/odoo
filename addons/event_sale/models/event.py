# -*- coding: utf-8 -*-

from openerp import models, fields, api, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import Warning


class event_event(models.Model):
    _inherit = 'event.event'

    event_ticket_ids = fields.One2many(
        'event.event.ticket', 'event_id', string='Event Ticket',
            default=lambda rec: rec._default_tickets(), copy=True)
    seats_max = fields.Integer(
        string='Maximum Available Seats',
        help="The maximum registration level is equal to the sum of the maximum registration of event ticket. " +
             "If you have too much registrations you are not able to confirm your event. (0 to ignore this rule )",
        store=True, readonly=True, compute='_compute_seats_max')

    badge_back = fields.Html('Badge Back', translate=True, states={'done': [('readonly', True)]})
    badge_innerleft = fields.Html('Badge Innner Left', translate=True, states={'done': [('readonly', True)]})
    badge_innerright = fields.Html('Badge Inner Right', translate=True, states={'done': [('readonly', True)]})

    @api.model
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

    @api.one
    @api.depends('event_ticket_ids.seats_max')
    def _compute_seats_max(self):
        self.seats_max = sum(ticket.seats_max for ticket in self.event_ticket_ids)


class event_ticket(models.Model):
    _name = 'event.event.ticket'
    _description = 'Event Ticket'

    name = fields.Char('Name', required=True, translate=True)
    event_id = fields.Many2one('event.event', "Event", required=True, ondelete='cascade')
    product_id = fields.Many2one(
        'product.product', 'Product',
        required=True, domain=[("event_type_id", "!=", False)],
        default=lambda self: self._default_product_id())
    registration_ids = fields.One2many('event.registration', 'event_ticket_id', 'Registrations')
    price = fields.Float('Price', digits=dp.get_precision('Product Price'))
    price_reduce = fields.Float("Price Reduce", compute="_get_price_compute", store=False,
                                digits=dp.get_precision('Product Price'))
    deadline = fields.Date("Sales End")
    is_expired = fields.Boolean('Is Expired', compute='_is_expired', store=True)

    @api.model
    def _default_product_id(self):
        try:
            product = self.env['ir.model.data'].get_object('event_sale', 'product_product_event')
            return product.id
        except ValueError:
            return False

    @api.one
    @api.depends('deadline')
    def _is_expired(self):
        # FIXME: A ticket is considered expired when the deadline is passed. The deadline should
        #        be considered in the timezone of the event, not the timezone of the user!
        #        Until we add a TZ on the event we'll use the context's current date, more accurate
        #        than using UTC all the time.
        current_date = fields.Date.context_today(self.with_context({'tz': self.event_id.date_tz}))
        self.is_expired = self.deadline < current_date

    @api.one
    @api.depends('price', 'product_id.lst_price', 'product_id.price')
    def _get_price_compute(self):
        product = self.product_id
        discount = product.lst_price and (product.lst_price - product.price) / product.lst_price or 0.0
        self.price_reduce = (1.0 - discount) * self.price

    seats_max = fields.Integer('Maximum Available Seats', help="You can for each event define a maximum registration level. If you have too much registrations you are not able to confirm your event. (put 0 to ignore this rule )")
    seats_reserved = fields.Integer(string='Reserved Seats', compute='_compute_seats', store=True)
    seats_available = fields.Integer(string='Available Seats', compute='_compute_seats', store=True)
    seats_unconfirmed = fields.Integer(string='Unconfirmed Seat Reservations', compute='_compute_seats', store=True)
    seats_used = fields.Integer(compute='_compute_seats', store=True)

    @api.multi
    @api.depends('seats_max', 'registration_ids.state')
    def _compute_seats(self):
        """ Determine reserved, available, reserved but unconfirmed and used seats. """
        # initialize fields to 0
        for ticket in self:
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
            self._cr.execute(query, (tuple(self.ids),))
            for event_ticket_id, state, num in self._cr.fetchall():
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
            raise Warning('No more available seats for the ticket')

    @api.onchange('product_id')
    def onchange_product_id(self):
        price = self.product_id.list_price if self.product_id else 0
        return {'value': {'price': price}}


class event_registration(models.Model):
    _inherit = 'event.registration'

    event_ticket_id = fields.Many2one('event.event.ticket', 'Event Ticket')
    # sale_order_line_id = fields.Many2one('sale.order.line', 'Sale Order Line', ondelete='cascade')

    @api.one
    @api.constrains('event_ticket_id', 'state')
    def _check_ticket_seats_limit(self):
        if self.event_ticket_id.seats_max and self.event_ticket_id.seats_available < 0:
            raise Warning('No more available seats for this ticket')

    @api.one
    def _check_auto_confirmation(self):
        res = super(event_registration, self)._check_auto_confirmation()[0]
        if res and self.origin:
            orders = self.env['sale.order'].search([('name', '=', self.origin)], limit=1)
            if orders and orders[0].state == 'draft':
                res = False
        return res

    @api.model
    def create(self, vals):
        res = super(event_registration, self).create(vals)
        if res.origin:
            message = _("The registration has been created for event %(event_name)s%(ticket)s from sale order %(order)s") % ({
                'event_name': '<i>%s</i>' % res.event_id.name,
                'ticket': res.event_ticket_id and _(' with ticket %s') % (('<i>%s</i>') % res.event_ticket_id.name) or '',
                'order': res.origin})
            res.message_post(body=message)
        return res
