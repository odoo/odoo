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

from osv import fields, osv
from tools.translate import _

class product(osv.osv):
    _inherit = 'product.product'
    _columns = {
        'event_ok': fields.boolean('Event Subscription', help='Determine if a product needs to create automatically an event registration at the confirmation of a sale order line.'),
        'event_type_id': fields.many2one('event.type', 'Type of Event', help='Filter the list of event on this category only, in the sale order lines'),
    }

    def onchange_event_ok(self, cr, uid, ids, event_ok, context=None):
        return {'value': {'type': event_ok and 'service' or False}}

product()

class sale_order_line(osv.osv):
    _inherit = 'sale.order.line'
    _columns = {
        'event_id': fields.many2one('event.event', 'Event', help="Choose an event and it will authomaticaly create a registration for this event"),
        #those 2 fields are used for dynamic domains and filled by onchange
        'event_type_id': fields.related('event_type_id', type='many2one', relation="event.type", string="Event Type"),
        'event_ok': fields.related('event_ok', string='event_ok', type='boolean'),
    }

    def product_id_change(self, cr, uid, ids,
                          pricelist, 
                          product, qty=0,
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
        create registration with sale order
        '''
        registration_obj = self.pool.get('event.registration')
        sale_obj = self.pool.get('sale.order')
        for order_line in self.browse(cr, uid, ids, context=context):
            if order_line.event_id.id:
                dic = {
                    'name': order_line.order_id.partner_invoice_id.name,
                    'partner_id': order_line.order_id.partner_id.id,
                    'contact_id': order_line.order_id.partner_invoice_id.id,
                    'nb_register': int(order_line.product_uom_qty),
                    'email': order_line.order_id.partner_id.email,
                    'phone': order_line.order_id.partner_id.phone,
                    'street': order_line.order_id.partner_invoice_id.street,
                    'city': order_line.order_id.partner_invoice_id.city,
                    'origin': order_line.order_id.name,
                    'event_id': order_line.event_id.id,
                }
                registration_id = registration_obj.create(cr, uid, dic, context=context)
                message = _("The registration %s has been created from the Sale Order %s.") % (registration_id, order_line.order_id.name)
                registration_obj.log(cr, uid, registration_id, message)
        return super(sale_order_line, self).button_confirm(cr, uid, ids, context=context)
