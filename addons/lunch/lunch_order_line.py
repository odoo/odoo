# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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
import addons
import tools
import pytz
import time
from osv import osv, fields
from datetime import datetime, timedelta

class lunch_order_line(osv.Model): #define each product that will be in one ORDER.
    """ lunch order line """
    _name = 'lunch.order.line'
    _description = 'lunch order line'

    def _price_get(self,cr,uid,ids,name,arg,context=None):
        orderLines = self.browse(cr,uid,ids,context=context)
        result={}
        for orderLine in orderLines:
            result[orderLine.id]=orderLine.product.price
        return result

    def onchange_price(self,cr,uid,ids,product,context=None):
        if product:
            price = self.pool.get('lunch.product').read(cr, uid, product, ['price'])['price']
            return {'value': {'price': price}}
        return {'value': {'price': 0.0}} 


    def confirm(self,cr,uid,ids,context=None):
        #confirm one or more order.line, update order status and create new cashmove
        cashmove_ref = self.pool.get('lunch.cashmove')
        orders_ref = self.pool.get('lunch.order')

        for order in self.browse(cr,uid,ids,context=context):
            if order.state!='confirmed':
                new_id = cashmove_ref.create(cr,uid,{'user_id': order.user_id.id, 'amount':0 - order.price,'description':order.product.name, 'order_id':order.id, 'state':'order', 'date':order.date})
                self.write(cr,uid,[order.id],{'cashmove':[('0',new_id)], 'state':'confirmed'},context)
        for order in self.browse(cr,uid,ids,context=context):
            isconfirmed = True
            for product in order.order_id.products:
                if product.state == 'new':
                    isconfirmed = False
                if product.state == 'cancelled':
                    isconfirmed = False
                    orders_ref.write(cr,uid,[order.order_id.id],{'state':'partially'},context)
            if isconfirmed == True:
                orders_ref.write(cr,uid,[order.order_id.id],{'state':'confirmed'},context)
        return {}

    def cancel(self,cr,uid,ids,context=None):
        #confirm one or more order.line, update order status and create new cashmove
        cashmove_ref = self.pool.get('lunch.cashmove')
        orders_ref = self.pool.get('lunch.order')

        for order in self.browse(cr,uid,ids,context=context):
            self.write(cr,uid,[order.id],{'state':'cancelled'},context)
            for cash in order.cashmove:
                cashmove_ref.unlink(cr,uid,cash.id,context)
        for order in self.browse(cr,uid,ids,context=context):
            hasconfirmed = False
            hasnew = False
            for product in order.order_id.products:
                if product.state=='confirmed':
                    hasconfirmed= True
                if product.state=='new':
                    hasnew= True
            if hasnew == False:
                if hasconfirmed == False:
                    orders_ref.write(cr,uid,[order.order_id.id],{'state':'cancelled'},context)
                    return {}
            orders_ref.write(cr,uid,[order.order_id.id],{'state':'partially'},context)
        return {}

    _columns = {
        'date' : fields.related('order_id','date',type='date', string="Date", readonly=True,store=True),
        'supplier' : fields.related('product','supplier',type='many2one',relation='res.partner',string="Supplier",readonly=True,store=True),
        'user_id' : fields.related('order_id', 'user_id', type='many2one', relation='res.users', string='User', readonly=True, store=True),
        'product' : fields.many2one('lunch.product','Product',required=True), #one offer can have more than one product and one product can be in more than one offer.
        'note' : fields.text('Note',size=256,required=False),
        'order_id' : fields.many2one('lunch.order','Order',ondelete='cascade'),
        'price' : fields.function(_price_get, string="Price",store=True),
        'state': fields.selection([('new', 'New'),('confirmed','Confirmed'), ('cancelled','Cancelled')], \
            'Status', readonly=True, select=True),
        'cashmove': fields.one2many('lunch.cashmove','order_id','Cash Move',ondelete='cascade'),
        
    }
    _defaults = {
        'state': lambda self, cr, uid, context: 'new',        
    }

