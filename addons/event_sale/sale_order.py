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
    'event_ok':fields.boolean('Event',help='Match a product with an event'),
    'event_type_id':fields.many2one('event.type','Type of Event'),
    }
product()

class sale_order_line(osv.osv):
    _inherit='sale.order.line'
    _columns={
        'event':fields.many2one('event.event','Event',help="Choose an event and it will authomaticaly create a registration for this event"),
        'event_type_id':fields.related('event_type',type='many2one', relation="event.type", string="Event Type"),
        'event_ok':fields.related('event_ok',string='event_ok' ,type='boolean'),
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
        res = super(sale_order_line,self).product_id_change(cr,uid,ids,pricelist, product, qty,uom, qty_uos, uos, name, partner_id,lang, update_tax, date_order, packaging, fiscal_position, flag,context)
        if product:
            product_res = self.pool.get('product.product').browse(cr, uid, product,context=context)
            if product_res.event_type_id:
                res['value'].update({'event_type_id':product_res.event_type_id.id,'event_ok':product_res.event_ok})
        return res

    def button_confirm(self,cr,uid,ids,context=None):
        '''
        create registration with sale order

        '''
        for registration in self.browse(cr,uid,ids,context=context):
            if registration.event.id:
                dic = {
                'name':registration.order_id.partner_invoice_id.name,
                'partner_id':registration.order_id.partner_id.id,
                'contact_id':registration.order_id.partner_invoice_id.id,
                'nb_register':int(registration.product_uom_qty),
                'email':registration.order_id.partner_id.email,
                'phone':registration.order_id.partner_id.phone,
                'street':registration.order_id.partner_invoice_id.street,
                'city':registration.order_id.partner_invoice_id.city,
                'origin':registration.order_id.name,
                'event_id':registration.event.id,
                }
                self.pool.get('event.registration').create(cr,uid,dic,context=context)
                message = ("A registration is create from the %s sale order.") % (registration.order_id.name,)
                self.pool.get('event.registration').log(cr, uid, registration.event.id, message)
        return super(sale_order_line, self).button_confirm(cr, uid, ids, context)


    def copy(self, cr, uid, id, default=None, context=None):
        print 'wwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwww'
        if not default:
            default = {}
            default.update({
                'event_id',1
                  })
        print '<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<'
        return super(sale_order, self).copy(cr, uid, id, default, context=context)

