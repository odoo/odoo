# -*- coding: utf-8 -*-

from openerp import models, fields, api, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError
from openerp.osv import fields as old_fields


class event_event(models.Model):
    _inherit = 'event.event'

    event_ticket_ids = fields.One2many(
        'event.event.ticket', 'event_id', string='Event Ticket',
        default=lambda rec: rec._default_tickets(), copy=True)

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


class event_ticket(models.Model):
    _name = 'event.event.ticket'
    _description = 'Event Ticket'

    name = fields.Char('Name', required=True, translate=True)
    event_id = fields.Many2one('event.event', "Event", required=True, ondelete='cascade')
    product_id = fields.Many2one(
        'product.product', 'Product',
        required=True, domain=["|", ("event_type_id", "!=", False), ("event_ok", "=", True)],
        default=lambda self: self._default_product_id())
    registration_ids = fields.One2many('event.registration', 'event_ticket_id', 'Registrations')
    price = fields.Float('Price', digits=dp.get_precision('Product Price'))
    deadline = fields.Date("Sales End")
    is_expired = fields.Boolean('Is Expired', compute='_is_expired')

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
        if self.deadline:
            current_date = fields.Date.context_today(self.with_context({'tz': self.event_id.date_tz}))
            self.is_expired = self.deadline < current_date
        else:
            self.is_expired = False

    # FIXME non-stored fields wont ends up in _columns (and thus _all_columns), which forbid them
    #       to be used in qweb views. Waiting a fix, we create an old function field directly.
    """
    price_reduce = fields.Float("Price Reduce", compute="_get_price_reduce", store=False,
                                digits=dp.get_precision('Product Price'))
    @api.one
    @api.depends('price', 'product_id.lst_price', 'product_id.price')
    def _get_price_reduce(self):
        product = self.product_id
        discount = product.lst_price and (product.lst_price - product.price) / product.lst_price or 0.0
        self.price_reduce = (1.0 - discount) * self.price
    """
    def _get_price_reduce(self, cr, uid, ids, field_name, arg, context=None):
        res = dict.fromkeys(ids, 0.0)
        for ticket in self.browse(cr, uid, ids, context=context):
            product = ticket.product_id
            discount = product.lst_price and (product.lst_price - product.price) / product.lst_price or 0.0
            res[ticket.id] = (1.0 - discount) * ticket.price
        return res

    _columns = {
        'price_reduce': old_fields.function(_get_price_reduce, type='float', string='Price Reduce',
                                            digits_compute=dp.get_precision('Product Price')),
    }

    # seats fields
    seats_availability = fields.Selection(
        [('limited', 'Limited'), ('unlimited', 'Unlimited')],
        'Available Seat', required=True, store=True, compute='_compute_seats', default="limited")
    seats_max = fields.Integer('Maximum Available Seats',
                               help="Define the number of available tickets. If you have too much registrations you will "
                                    "not be able to sell tickets anymore. Set 0 to ignore this rule set as unlimited.")
    seats_reserved = fields.Integer(string='Reserved Seats', compute='_compute_seats', store=True)
    seats_available = fields.Integer(string='Available Seats', compute='_compute_seats', store=True)
    seats_unconfirmed = fields.Integer(string='Unconfirmed Seat Reservations', compute='_compute_seats', store=True)
    seats_used = fields.Integer(compute='_compute_seats', store=True)

    @api.multi
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
            raise UserError(_('No more available seats for the ticket'))

    @api.onchange('product_id')
    def onchange_product_id(self):
        price = self.product_id.list_price if self.product_id else 0
        return {'value': {'price': price}}


class event_registration(models.Model):
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

    @api.multi
    def _check_auto_confirmation(self):
        res = super(event_registration, self)._check_auto_confirmation()
        if res:
            orders = self.env['sale.order'].search([('state', '=', 'draft'), ('id', 'in', self.mapped('sale_order_id').ids)], limit=1)
            if orders:
                res = False
        return res

    @api.model
    def create(self, vals):
        res = super(event_registration, self).create(vals)
        if res.origin or res.sale_order_id:
            message = _("The registration has been created for event %(event_name)s%(ticket)s from sale order %(order)s") % ({
                'event_name': '<i>%s</i>' % res.event_id.name,
                'ticket': res.event_ticket_id and _(' with ticket %s') % (('<i>%s</i>') % res.event_ticket_id.name) or '',
                'order': res.origin or res.sale_order_id.name})
            res.message_post(body=message)
        return res

    @api.model
    def _prepare_attendee_values(self, registration):
        """ Override to add sale related stuff """
        line_id = registration.get('sale_order_line_id')
        if line_id:
            registration.setdefault('partner_id', line_id.order_id.partner_id)
        att_data = super(event_registration, self)._prepare_attendee_values(registration)
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
