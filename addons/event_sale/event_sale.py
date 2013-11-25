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

from openerp.osv import fields, osv
from openerp.tools.translate import _

class product(osv.osv):
    _inherit = 'product.template'
    _columns = {
        'event_ok': fields.boolean('Event Subscription', help='Determine if a product needs to create automatically an event registration at the confirmation of a sales order line.'),
        'event_type_id': fields.many2one('event.type', 'Type of Event', help='Select event types so when we use this product in sales order lines, it will filter events of this type only.'),
    }

    def onchange_event_ok(self, cr, uid, ids, type, event_ok, context=None):
        return {'value': {'type': event_ok and 'service' or type != 'service' and type or False}}


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
                res['value'].update({'event_type_id': product_res.event_type_id.id, 'event_ok':product_res.event_ok})
        return res

    def button_confirm(self, cr, uid, ids, context=None):
        '''
        create registration with sales order
        '''
        if context is None:
            context = {}
        registration_obj = self.pool.get('event.registration')
        for order_line in self.browse(cr, uid, ids, context=context):
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
                    if order_line.event_ticket_id.register_avail != 9999 and dic['nb_register'] > order_line.event_ticket_id.register_avail:
                        raise osv.except_osv(_('Error!'), _('There are not enough tickets available (%s) for %s' % (order_line.event_ticket_id.register_avail, order_line.event_ticket_id.name)))
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

    def _get_register_max(self, cr, uid, ids, field_name, arg, context=None):
        result = dict.fromkeys(ids, 0)
        for rec in self.browse(cr, uid, ids, context=context):
            result[rec.id] = sum([ep.register_max for ep in rec.event_ticket_ids])
        return result

    _columns = {
        'event_ticket_ids': fields.one2many('event.event.ticket', "event_id", "Event Ticket"),
        'register_max': fields.function(_get_register_max,
            string='Maximum Registrations',
            help="The maximum registration level is equal to the sum of the maximum registration of event ticket." +
            "If you have too much registrations you are not able to confirm your event. (0 to ignore this rule )",
            type='integer')
    }

    def check_registration_limits(self, cr, uid, ids, context=None):
        for event in self.browse(cr, uid, ids, context=context):
            if event.event_ticket_ids:
                event.event_ticket_ids.check_registration_limits_before(0)
        return super(event_event, self).check_registration_limits(cr, uid, ids, context=context)


class event_ticket(osv.osv):
    _name = 'event.event.ticket'

    def _get_register(self, cr, uid, ids, fields, args, context=None):
        """Get Confirm or uncofirm register value.
        @param ids: List of Event Ticket registration type's id
        @param fields: List of function fields(register_current and register_prospect).
        @param context: A standard dictionary for contextual values
        @return: Dictionary of function fields value.
        """
        res = {}
        for event in self.browse(cr, uid, ids, context=context):
            res[event.id] = {}
            reg_open = reg_done = reg_draft =0
            for registration in event.registration_ids:
                if registration.state == 'open':
                    reg_open += registration.nb_register
                elif registration.state == 'done':
                    reg_done += registration.nb_register
                elif registration.state == 'draft':
                    reg_draft += registration.nb_register
            for field in fields:
                number = 0
                if field == 'register_current':
                    number = reg_open
                elif field == 'register_attended':
                    number = reg_done
                elif field == 'register_prospect':
                    number = reg_draft
                elif field == 'register_avail':
                    #the number of ticket is unlimited if the event.register_max field is not set.
                    #In that cas we arbitrary set it to 9999, it is used in the kanban view to special case the display of the 'subscribe' button
                    number = event.register_max - reg_open if event.register_max != 0 else 9999
                res[event.id][field] = number
        return res

    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'event_id': fields.many2one('event.event', "Event", required=True, ondelete='cascade'),
        'product_id': fields.many2one('product.product', 'Product', required=True, domain=[("event_type_id", "!=", False)]),
        'registration_ids': fields.one2many('event.registration', 'event_ticket_id', 'Registrations'),
        'deadline': fields.date("Sales End"),
        'price': fields.float('Price'),
        'register_max': fields.integer('Maximum Registrations'),
        'register_current': fields.function(_get_register, string='Current Registrations', type='integer', multi='register_numbers'),
        'register_avail': fields.function(_get_register, string='Available Registrations', type='integer', multi='register_numbers'),
        'register_prospect': fields.function(_get_register, string='Unconfirmed Registrations', type='integer', multi='register_numbers'),
        'register_attended': fields.function(_get_register, string='# of Participations', type='integer', multi='register_numbers'),
    }

    def check_registration_limits_before(self, cr, uid, ids, number, context=None):
        for ticket in self.browse(cr, uid, ids, context=context):
            if ticket.register_max:
                if not ticket.register_avail:
                    raise osv.except_osv(_('Warning!'),_('No Tickets Available for "%s"' % ticket.name))
                elif number + ticket.register_current > ticket.register_max:
                    raise osv.except_osv(_('Warning!'), _('There only %d tickets available for "%s"' % (ticket.register_avail, ticket.name)))
        return True

    def onchange_product_id(self, cr, uid, ids, product_id=False, context=None):
        return {'value': {'price': self.pool.get("product.product").browse(cr, uid, product_id).list_price or 0}}


class event_registration(osv.osv):
    """Event Registration"""
    _inherit= 'event.registration'
    _columns = {
        'event_ticket_id': fields.many2one('event.event.ticket', 'Event Ticket'),
    }

    def registration_open(self, cr, uid, ids, context=None):
        """ Open Registration
        """
        for registration in self.browse(cr, uid, ids, context=context):
            if registration.event_ticket_id:
                registration.event_ticket_id.check_registration_limits_before(1)
        return super(event_registration, self).registration_open(cr, uid, ids, context=context)
