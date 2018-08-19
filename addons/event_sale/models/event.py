# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

from odoo.addons import decimal_precision as dp
from odoo.tools import float_is_zero


class EventType(models.Model):
    _inherit = 'event.type'

    @api.model
    def _get_default_event_ticket_ids(self):
        product = self.env.ref('event_sale.product_product_event', raise_if_not_found=False)
        if not product:
            return False
        return [(0, 0, {
            'name': _('Registration'),
            'product_id': product.id,
            'price': 0,
        })]

    use_ticketing = fields.Boolean('Ticketing')
    event_ticket_ids = fields.One2many(
        'event.event.ticket', 'event_type_id',
        string='Tickets', default=_get_default_event_ticket_ids)

    @api.onchange('name')
    def _onchange_name(self):
        if self.name:
            self.event_ticket_ids.filtered(lambda ticket: ticket.name == _('Registration')).update({
                'name': _('Registration for %s') % self.name
            })


class Event(models.Model):
    _inherit = 'event.event'

    event_ticket_ids = fields.One2many(
        'event.event.ticket', 'event_id', string='Event Ticket',
        copy=True)

    @api.onchange('event_type_id')
    def _onchange_type(self):
        super(Event, self)._onchange_type()
        if self.event_type_id.use_ticketing:
            self.event_ticket_ids = [(5, 0, 0)] + [
                (0, 0, {
                    'name': self.name and _('Registration for %s') % self.name or ticket.name,
                    'product_id': ticket.product_id.id,
                    'price': ticket.price,
                })
                for ticket in self.event_type_id.event_ticket_ids]

    @api.multi
    def _is_event_registrable(self):
        self.ensure_one()
        if not self.event_ticket_ids:
            return True
        return all(self.event_ticket_ids.with_context(active_test=False).mapped(lambda t: t.product_id.active))

class EventTicket(models.Model):
    _name = 'event.event.ticket'
    _description = 'Event Ticket'

    def _default_product_id(self):
        return self.env.ref('event_sale.product_product_event', raise_if_not_found=False)

    name = fields.Char(string='Name', required=True, translate=True)
    event_type_id = fields.Many2one('event.type', string='Event Category', ondelete='cascade')
    event_id = fields.Many2one('event.event', string="Event", ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product',
        required=True, domain=[("event_ok", "=", True)],
        default=_default_product_id)
    registration_ids = fields.One2many('event.registration', 'event_ticket_id', string='Registrations')
    price = fields.Float(string='Price', digits=dp.get_precision('Product Price'))
    deadline = fields.Date(string="Sales End")
    is_expired = fields.Boolean(string='Is Expired', compute='_compute_is_expired')

    price_reduce = fields.Float(string="Price Reduce", compute="_compute_price_reduce", digits=dp.get_precision('Product Price'))
    price_reduce_taxinc = fields.Float(compute='_get_price_reduce_tax', string='Price Reduce Tax inc')
    # seats fields
    seats_availability = fields.Selection([('limited', 'Limited'), ('unlimited', 'Unlimited')],
        string='Available Seat', required=True, store=True, compute='_compute_seats', default="limited")
    seats_max = fields.Integer(string='Maximum Available Seats',
       help="Define the number of available tickets. If you have too much registrations you will "
            "not be able to sell tickets anymore. Set 0 to ignore this rule set as unlimited.")
    seats_reserved = fields.Integer(string='Reserved Seats', compute='_compute_seats', store=True)
    seats_available = fields.Integer(string='Available Seats', compute='_compute_seats', store=True)
    seats_unconfirmed = fields.Integer(string='Unconfirmed Seat Reservations', compute='_compute_seats', store=True)
    seats_used = fields.Integer(compute='_compute_seats', store=True)

    @api.multi
    def _compute_is_expired(self):
        for record in self:
            if record.deadline:
                current_date = fields.Date.context_today(record.with_context({'tz': record.event_id.date_tz}))
                record.is_expired = record.deadline < current_date
            else:
                record.is_expired = False

    @api.multi
    def _compute_price_reduce(self):
        for record in self:
            product = record.product_id
            discount = product.lst_price and (product.lst_price - product.price) / product.lst_price or 0.0
            record.price_reduce = (1.0 - discount) * record.price

    def _get_price_reduce_tax(self):
        for record in self:
            # sudo necessary here since the field is most probably accessed through the website
            tax_ids = record.sudo().product_id.taxes_id.filtered(lambda r: r.company_id == record.event_id.company_id)
            taxes = tax_ids.compute_all(record.price_reduce, record.event_id.company_id.currency_id, 1.0, product=record.product_id)
            record.price_reduce_taxinc = taxes['total_included']

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
            self.env.cr.execute(query, (tuple(self.ids),))
            for event_ticket_id, state, num in self.env.cr.fetchall():
                ticket = self.browse(event_ticket_id)
                ticket[state_field[state]] += num
        # compute seats_available
        for ticket in self:
            if ticket.seats_max > 0:
                ticket.seats_available = ticket.seats_max - (ticket.seats_reserved + ticket.seats_used)

    @api.multi
    @api.constrains('registration_ids', 'seats_max')
    def _check_seats_limit(self):
        for record in self:
            if record.seats_max and record.seats_available < 0:
                raise ValidationError(_('No more available seats for this ticket type.'))

    @api.constrains('event_type_id', 'event_id')
    def _constrains_event(self):
        if any(ticket.event_type_id and ticket.event_id for ticket in self):
            raise UserError(_('Ticket cannot belong to both the event category and the event itself.'))

    @api.onchange('product_id')
    def _onchange_product_id(self):
        self.price = self.product_id.list_price or 0

    def get_ticket_multiline_description_sale(self):
        """ Compute a multiline description of this ticket, in the context of sales.
            It will often be used as the default description of a sales order line referencing this ticket.

        1. the first line is the ticket name
        2. the second line is the event name (if it exists, which should be the case with a normal workflow) or the product name (if it exists)

        We decided to ignore entirely the product name and the product description_sale because they are considered to be replaced by the ticket name and event name.
            -> the workflow of creating a new event also does not lead to filling them correctly, as the product is created through the event interface
        """

        name = self.display_name

        if self.event_id:
            name += '\n' + self.event_id.display_name
        elif self.product_id:
            name += '\n' + self.product_id.display_name

        return name


class EventRegistration(models.Model):
    _inherit = 'event.registration'

    event_ticket_id = fields.Many2one('event.event.ticket', string='Event Ticket', readonly=True, states={'draft': [('readonly', False)]})
    # in addition to origin generic fields, add real relational fields to correctly
    # handle attendees linked to sales orders and their lines
    # TDE FIXME: maybe add an onchange on sale_order_id + origin
    sale_order_id = fields.Many2one('sale.order', string='Source Sales Order', ondelete='cascade')
    sale_order_line_id = fields.Many2one('sale.order.line', string='Sales Order Line', ondelete='cascade')

    @api.onchange('event_id')
    def _onchange_event_id(self):
        # We reset the ticket when keeping it would lead to an inconstitent state.
        if self.event_ticket_id and (not self.event_id or self.event_id != self.event_ticket_id.event_id):
            self.event_ticket_id = None

    @api.multi
    @api.constrains('event_ticket_id', 'state')
    def _check_ticket_seats_limit(self):
        for record in self:
            if record.event_ticket_id.seats_max and record.event_ticket_id.seats_available < 0:
                raise ValidationError(_('No more available seats for this ticket'))

    @api.multi
    def _check_auto_confirmation(self):
        res = super(EventRegistration, self)._check_auto_confirmation()
        if res:
            orders = self.env['sale.order'].search([('state', '=', 'draft'), ('id', 'in', self.mapped('sale_order_id').ids)], limit=1)
            if orders:
                res = False
        return res

    @api.model
    def create(self, vals):
        res = super(EventRegistration, self).create(vals)
        if res.origin or res.sale_order_id:
            res.message_post_with_view('mail.message_origin_link',
                values={'self': res, 'origin': res.sale_order_id},
                subtype_id=self.env.ref('mail.mt_note').id)
        return res

    @api.model
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

    @api.multi
    def summary(self):
        res = super(EventRegistration, self).summary()
        if self.event_ticket_id.product_id.image_medium:
            res['image'] = '/web/image/product.product/%s/image_medium' % self.event_ticket_id.product_id.id
        information = res.setdefault('information', {})
        information.append((_('Name'), self.name))
        information.append((_('Ticket'), self.event_ticket_id.name or _('None')))
        order = self.sale_order_id.sudo()
        order_line = self.sale_order_line_id.sudo()
        if not order or float_is_zero(order_line.price_total, precision_digits=order.currency_id.rounding):
            payment_status = _('Free')
        elif not order.invoice_ids or any(invoice.state != 'paid' for invoice in order.invoice_ids):
            payment_status = _('To pay')
            res['alert'] = _('The registration must be paid')
        else:
            payment_status = _('Paid')
        information.append((_('Payment'), payment_status))
        return res
