# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import api
from openerp.fields import Integer, One2many, Html
from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp

class product_template(osv.osv):
    _inherit = 'product.template'
    _columns = {
        'event_ok': fields.boolean('Event Subscription', help='Determine if a product needs to create automatically an event registration at the confirmation of a sales order line.'),
        'event_type_id': fields.many2one('event.type', 'Type of Event', help='Select event types so when we use this product in sales order lines, it will filter events of this type only.'),
    }

    def onchange_event_ok(self, cr, uid, ids, type, event_ok, context=None):
        if event_ok:
            return {'value': {'type': 'service'}}
        return {}

class product(osv.osv):
    _inherit = 'product.product'
    _columns = {
        'event_ticket_ids': fields.one2many('event.event.ticket', 'product_id', 'Event Tickets'),
    }

    def onchange_event_ok(self, cr, uid, ids, type, event_ok, context=None):
        # cannot directly forward to product.template as the ids are theoretically different
        if event_ok:
            return {'value': {'type': 'service'}}
        return {}


class sale_order_line(osv.osv):
    _inherit = 'sale.order.line'
    _columns = {
        'event_id': fields.many2one('event.event', 'Event',
            help="Choose an event and it will automatically create a registration for this event."),
        'event_ticket_id': fields.many2one('event.event.ticket', 'Event Ticket',
            help="Choose an event ticket and it will automatically create a registration for this event ticket."),
        #those 2 fields are used for dynamic domains and filled by onchange
        'event_type_id': fields.related('product_id','event_type_id', type='many2one', relation="event.type", string="Event Type"),
        'event_ok': fields.related('product_id', 'event_ok', string='event_ok', type='boolean'),
    }

    def _prepare_order_line_invoice_line(self, cr, uid, line, account_id=False, context=None):
        res = super(sale_order_line, self)._prepare_order_line_invoice_line(cr, uid, line, account_id=account_id, context=context)
        if line.event_id:
            event = self.pool['event.event'].read(cr, uid, line.event_id.id, ['name'], context=context)
            res['name'] = '%s: %s' % (res['name'], event['name'])
        return res

    def product_id_change(self, cr, uid, ids,
                          pricelist, 
                          product,
                          qty=0,
                          uom=False,
                          qty_uos=0,
                          uos=False,
                          name='',
                          partner_id=False,
                          lang=False,
                          update_tax=True,
                          date_order=False,
                          packaging=False,
                          fiscal_position=False,
                          flag=False, context=None):
        """
        check product if event type
        """
        res = super(sale_order_line,self).product_id_change(cr, uid, ids, pricelist, product, qty=qty, uom=uom, qty_uos=qty_uos, uos=uos, name=name, partner_id=partner_id, lang=lang, update_tax=update_tax, date_order=date_order, packaging=packaging, fiscal_position=fiscal_position, flag=flag, context=context)
        if product:
            product_res = self.pool.get('product.product').browse(cr, uid, product, context=context)
            if product_res.event_ok:
                res['value'].update(event_type_id=product_res.event_type_id.id,
                                    event_ok=product_res.event_ok)
            else:
                res['value'].update(event_type_id=False,
                                    event_ok=False)
        return res

    def button_confirm(self, cr, uid, ids, context=None):
        '''
        create registration with sales order
        '''
        context = dict(context or {})
        registration_obj = self.pool.get('event.registration')
        for order_line in self.browse(cr, uid, ids, context=context):
            if order_line.state == 'cancel':
                continue
            if order_line.event_id:
                dic = {
                    'name': order_line.order_id.partner_invoice_id.name,
                    'partner_id': order_line.order_id.partner_id.id,
                    'nb_register': int(order_line.product_uom_qty),
                    'email': order_line.order_id.partner_id.email,
                    'phone': order_line.order_id.partner_id.phone,
                    'origin': order_line.order_id.name,
                    'event_id': order_line.event_id.id,
                    'event_ticket_id': order_line.event_ticket_id and order_line.event_ticket_id.id or None,
                }

                if order_line.event_ticket_id:
                    message = _("The registration has been created for event <i>%s</i> with the ticket <i>%s</i> from the Sale Order %s. ") % (order_line.event_id.name, order_line.event_ticket_id.name, order_line.order_id.name)
                else:
                    message = _("The registration has been created for event <i>%s</i> from the Sale Order %s. ") % (order_line.event_id.name, order_line.order_id.name)
                
                context.update({'mail_create_nolog': True})
                registration_id = registration_obj.create(cr, uid, dic, context=context)
                registration_obj.message_post(cr, uid, [registration_id], body=message, context=context)
        return super(sale_order_line, self).button_confirm(cr, uid, ids, context=context)

    def onchange_event_ticket_id(self, cr, uid, ids, event_ticket_id=False, context=None):
        price = event_ticket_id and self.pool.get("event.event.ticket").browse(cr, uid, event_ticket_id, context=context).price or False
        return {'value': {'price_unit': price}}


class event_event(osv.osv):
    _inherit = 'event.event'

    event_ticket_ids = One2many('event.event.ticket', 'event_id', string='Event Ticket',
        default=lambda rec: rec._default_tickets(), copy=True)
    seats_max = Integer(string='Maximum Available Seats',
        help="The maximum registration level is equal to the sum of the maximum registration of event ticket. " +
            "If you have too much registrations you are not able to confirm your event. (0 to ignore this rule )",
        store=True, readonly=True, compute='_compute_seats_max')

    badge_back = Html('Badge Back', translate=True, states={'done': [('readonly', True)]})
    badge_innerleft = Html('Badge Innner Left', translate=True, states={'done': [('readonly', True)]})
    badge_innerright = Html('Badge Inner Right', translate=True, states={'done': [('readonly', True)]})

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
        if any(ticket.seats_max == 0 for ticket in self.event_ticket_ids):
            self.seats_max = 0
        else:
            self.seats_max = sum(ticket.seats_max for ticket in self.event_ticket_ids)

class event_ticket(osv.osv):
    _name = 'event.event.ticket'

    def _get_seats(self, cr, uid, ids, fields, args, context=None):
        """Get reserved, available, reserved but unconfirmed and used seats for each event tickets.
        @return: Dictionary of function field values.
        """
        res = dict([(id, {}) for id in ids])
        for ticket in self.browse(cr, uid, ids, context=context):
            res[ticket.id]['seats_reserved'] = sum(reg.nb_register for reg in ticket.registration_ids if reg.state == "open")
            res[ticket.id]['seats_used'] = sum(reg.nb_register for reg in ticket.registration_ids if reg.state == "done")
            res[ticket.id]['seats_unconfirmed'] = sum(reg.nb_register for reg in ticket.registration_ids if reg.state == "draft")
            res[ticket.id]['seats_available'] = ticket.seats_max - \
                (res[ticket.id]['seats_reserved'] + res[ticket.id]['seats_used']) \
                if ticket.seats_max > 0 else None
        return res

    def _is_expired(self, cr, uid, ids, field_name, args, context=None):
        # FIXME: A ticket is considered expired when the deadline is passed. The deadline should
        #        be considered in the timezone of the event, not the timezone of the user!
        #        Until we add a TZ on the event we'll use the context's current date, more accurate
        #        than using UTC all the time.
        current_date = fields.date.context_today(self, cr, uid, context=context)
        return {ticket.id: ticket.deadline and ticket.deadline < current_date
                      for ticket in self.browse(cr, uid, ids, context=context)}

    def _get_price_reduce(self, cr, uid, ids, field_name, arg, context=None):
        res = dict.fromkeys(ids, 0.0)
        for ticket in self.browse(cr, uid, ids, context=context):
            product = ticket.product_id
            discount = product.lst_price and (product.lst_price - product.price) / product.lst_price or 0.0
            res[ticket.id] = (1.0-discount) * ticket.price
        return res

    _columns = {
        'name': fields.char('Name', required=True, translate=True),
        'event_id': fields.many2one('event.event', "Event", required=True, ondelete='cascade'),
        'product_id': fields.many2one('product.product', 'Product', required=True,
            domain=["|", ("event_type_id", "!=", False), ("event_ok", "=", True)]),
        'registration_ids': fields.one2many('event.registration', 'event_ticket_id', 'Registrations'),
        'deadline': fields.date("Sales End"),
        'is_expired': fields.function(_is_expired, type='boolean', string='Is Expired'),
        'price': fields.float('Price', digits_compute=dp.get_precision('Product Price')),
        'price_reduce': fields.function(_get_price_reduce, type='float', string='Price Reduce', digits_compute=dp.get_precision('Product Price')),
        'seats_max': fields.integer('Maximum Available Seats', oldname='register_max', help="You can for each event define a maximum registration level. If you have too much registrations you are not able to confirm your event. (put 0 to ignore this rule )"),
        'seats_reserved': fields.function(_get_seats, string='Reserved Seats', type='integer', multi='seats_reserved'),
        'seats_available': fields.function(_get_seats, string='Available Seats', type='integer', multi='seats_reserved'),
        'seats_unconfirmed': fields.function(_get_seats, string='Unconfirmed Seat Reservations', type='integer', multi='seats_reserved'),
        'seats_used': fields.function(_get_seats, string='Number of Participations', type='integer', multi='seats_reserved'),
    }

    def _default_product_id(self, cr, uid, context={}):
        imd = self.pool.get('ir.model.data')
        try:
            product = imd.get_object(cr, uid, 'event_sale', 'product_product_event')
        except ValueError:
            return False
        return product.id

    _defaults = {
        'product_id': _default_product_id
    }

    def _check_seats_limit(self, cr, uid, ids, context=None):
        for ticket in self.browse(cr, uid, ids, context=context):
            if ticket.seats_max and ticket.seats_available < 0:
                return False
        return True

    _constraints = [
        (_check_seats_limit, 'No more available tickets.', ['registration_ids','seats_max']),
    ]

    def onchange_product_id(self, cr, uid, ids, product_id=False, context=None):
        price = self.pool.get("product.product").browse(cr, uid, product_id).list_price if product_id else 0
        return {'value': {'price': price}}


class event_registration(osv.osv):
    """Event Registration"""
    _inherit= 'event.registration'
    _columns = {
        'event_ticket_id': fields.many2one('event.event.ticket', 'Event Ticket'),
    }

    def _check_ticket_seats_limit(self, cr, uid, ids, context=None):
        for registration in self.browse(cr, uid, ids, context=context):
            if registration.event_ticket_id.seats_max and registration.event_ticket_id.seats_available < 0:
                return False
        return True

    _constraints = [
        (_check_ticket_seats_limit, 'No more available tickets.', ['event_ticket_id','nb_register','state']),
    ]
