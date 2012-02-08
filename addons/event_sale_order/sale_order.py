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
class product(osv.osv):
    _inherit='product.product'
    _columns={
    'event_ok':fields.boolean('Event'),
    'event_type':fields.many2one('event.type','Type of event'),
    }
product()

class sale_order_line(osv.osv):
    _inherit='sale.order.line'
    _columns={
    'event':fields.many2one('event.event','Event'),
    'event_type':fields.char('event_type',128),
    }
    def onchange_product(self,cr,uid,ids,product):
        product = self.pool.get('product.product').browse(cr, uid, product)
        if product.event_type:
            res={'value' : {
                            'event_type':product.event_type.name
                           }
                }
            return res

    def button_confirm(self,cr,uid,ids,context=None):
        registration = self.browse(cr,uid,ids,context=None)
        for registration in registration:
            self.pool.get('event.registration').create(cr,uid,{
            'name':registration.order_id.partner_invoice_id.name,
            'partner_id':registration.order_id.partner_id.id,
            'email':registration.order_id.partner_id.email,
            'phone':registration.order_id.partner_id.phone,
            'street':registration.order_id.partner_invoice_id.street,
            'city':registration.order_id.partner_invoice_id.city,
            'origin':registration.order_id.name,
            'nb_register':1,
            'event_id':registration.event.id,
            })
        return super(sale_order_line, self).button_confirm(cr, uid, ids, context)

sale_order_line()


