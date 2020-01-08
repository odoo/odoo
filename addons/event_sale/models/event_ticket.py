# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class EventTicket(models.Model):
    _name = 'event.event.ticket'
    _description = 'Event Ticket'

    def _default_product_id(self):
        return self.env.ref('event_sale.product_product_event', raise_if_not_found=False)

    name = fields.Char(string='Name', required=True, translate=True)
    event_type_id = fields.Many2one('event.type', string='Event Category', ondelete='cascade')
    event_id = fields.Many2one('event.event', string="Event", ondelete='cascade')
    company_id = fields.Many2one('res.company', related='event_id.company_id')
    # product
    product_id = fields.Many2one('product.product', string='Product',
        required=True, domain=[("event_ok", "=", True)],
        default=_default_product_id)
    price = fields.Float(string='Price', digits='Product Price')
    price_reduce = fields.Float(string="Price Reduce", compute="_compute_price_reduce", digits='Product Price')
    price_reduce_taxinc = fields.Float(compute='_get_price_reduce_tax', string='Price Reduce Tax inc')
    # sale
    start_sale_date = fields.Date(string="Sales Start")
    end_sale_date = fields.Date(string="Sales End")
    is_expired = fields.Boolean(string='Is Expired', compute='_compute_is_expired')
    sale_available = fields.Boolean(string='Is Available', compute='_compute_sale_available')
    registration_ids = fields.One2many('event.registration', 'event_ticket_id', string='Registrations')
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

    def _compute_is_expired(self):
        for ticket in self:
            if ticket.end_sale_date:
                current_date = fields.Date.context_today(ticket.with_context(tz=ticket.event_id.date_tz))
                ticket.is_expired = ticket.end_sale_date < current_date
            else:
                ticket.is_expired = False

    @api.depends('product_id.active', 'start_sale_date', 'end_sale_date')
    def _compute_sale_available(self):
        for ticket in self:
            current_date = fields.Date.context_today(ticket.with_context(tz=ticket.event_id.date_tz))
            if not ticket.product_id.active:
                ticket.sale_available = False
            elif ticket.start_sale_date and ticket.start_sale_date > current_date:
                ticket.sale_available = False
            elif ticket.end_sale_date and ticket.end_sale_date < current_date:
                ticket.sale_available = False
            else:
                ticket.sale_available = True

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
            self.env['event.registration'].flush(['event_id', 'event_ticket_id', 'state'])
            self.env.cr.execute(query, (tuple(self.ids),))
            for event_ticket_id, state, num in self.env.cr.fetchall():
                ticket = self.browse(event_ticket_id)
                ticket[state_field[state]] += num
        # compute seats_available
        for ticket in self:
            if ticket.seats_max > 0:
                ticket.seats_available = ticket.seats_max - (ticket.seats_reserved + ticket.seats_used)

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

    def _get_ticket_multiline_description_sale(self):
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

    @api.constrains('start_sale_date', 'end_sale_date')
    def _check_start_sale_date_and_end_sale_date(self):
        for ticket in self:
            if ticket.start_sale_date and ticket.end_sale_date and ticket.start_sale_date > ticket.end_sale_date:
                raise UserError(_('The stop date cannot be earlier than the start date.'))
