
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
from lxml import etree

class lunch_order(osv.Model):
    """ lunch order """
    _name = 'lunch.order'
    _description = 'Lunch Order'

    def _price_get(self,cr,uid,ids,name,arg,context=None):
        orders = self.browse(cr,uid,ids,context=context)
        result={}
        for order in orders:
            value = 0.0
            for product in order.products:
                if product.state != 'cancelled':
                    value+=product.product.price
                    result[order.id]=value
        return result

    def add_preference(self,cr,uid,ids,pref_id,context=None):
        pref_ref = self.pool.get("lunch.preference")
        orderline_ref = self.pool.get('lunch.order.line')
        order = self.browse(cr,uid,ids,context=context)[0]
        pref = pref_ref.browse(cr,uid,pref_id,context=context)
        prod_ref = self.pool.get('lunch.product')
        if pref["user_id"].id == uid:
            new_order_line = {}
            new_order_line['date'] = order["date"]
            new_order_line['user_id'] = uid
            new_order_line['product'] = pref["product"].id
            new_order_line['note'] = pref["note"]
            new_order_line['order_id'] = order.id
            new_order_line['price'] = pref["price"]
            new_order_line['supplier'] = prod_ref.browse(cr,uid,pref["product"].id,context=context)['supplier'].id
            new_id = orderline_ref.create(cr,uid,new_order_line)
            order.products.append(new_id)
            total = self._price_get(cr,uid,ids," "," ",context=context)
            self.write(cr,uid,ids,{'total':total},context)
        return True

    def _alerts_get(self,cr,uid,ids,name,arg,context=None):
        orders = self.browse(cr,uid,ids,context=context)
        alert_ref = self.pool.get('lunch.alert')
        alert_ids = alert_ref.search(cr,uid,[],context=context)
        result={}
        alert_msg= self._default_alerts_get(cr,uid,arg,context)
        for order in orders:
            if order.state=='new':
                result[order.id]=alert_msg
        return result

    def _default_alerts_get(self,cr,uid,arg,context=None):
        alert_ref = self.pool.get('lunch.alert')
        alert_ids = alert_ref.search(cr,uid,[],context=context)
        alert_msg=""
        for alert in alert_ref.browse(cr,uid,alert_ids,context=context):
            if alert :
                #there are alerts
                if alert.active==True:
                    #the alert is active
                    if alert.day=='specific':
                        #the alert is only activated a specific day
                        if alert.specific==fields.datetime.now().split(' ')[0]:
                            print alert.specific
                    elif alert.day=='week':
                        #the alert is activated during some days of the week
                        continue
                    elif alert.day=='days':
                        #the alert is activated everyday
                        if alert.active_from==alert.active_to:
                            #the alert is executing all the day
                            alert_msg+=" * "
                            alert_msg+=alert.message
                            alert_msg+='\n'
                        elif alert.active_from<alert.active_to:
                            #the alert is executing from ... to ...
                            now = datetime.utcnow()#.split(' ')[1] 
                            user = self.pool.get('res.users').browse(cr, uid, uid)
                            tz = pytz.timezone(user.tz) if user.tz else pytz.utc
                            tzoffset=tz.utcoffset(now)
                            mynow = now+tzoffset
                            hour_to = int(alert.active_to)
                            min_to = int((alert.active_to-hour_to)*60)
                            to_alert = datetime.strptime(str(hour_to)+":"+str(min_to),"%H:%M")
                            hour_from = int(alert.active_from)
                            min_from = int((alert.active_from-hour_from)*60)
                            from_alert = datetime.strptime(str(hour_from)+":"+str(min_from),"%H:%M")
                            if mynow.time()>=from_alert.time() and mynow.time()<=to_alert.time():
                                alert_msg+="* "
                                alert_msg+=alert.message
                                alert_msg+='\n'
        return alert_msg

    def onchange_price(self,cr,uid,ids,products,context=None):
        res = {'value':{'total':0.0}}
        if products:
            tot = 0.0
            for prod in products:
                orderline = {}
                if isinstance(prod[1],bool): 
                    orderline = prod[2]
                    tot += orderline['price']
                else:
                    orderline = self.pool.get('lunch.order.line').browse(cr,uid,prod[1],context=context)
                    tot += orderline.price
                res = {'value':{'total':tot}}
        return res

    def _default_product_get(self,cr,uid,args,context=None):
        cr.execute('''SELECT lol.id, lol.date, lol.user_id, lol.product, lol.note, lol.price, lol.write_date FROM lunch_order_line AS lol ORDER BY write_date''')
        res = cr.dictfetchall()
        result = []
        i=0
        pref_ref = self.pool.get('lunch.preference')
        for temp in res:
            if i==20:
                break
            if temp['user_id'] == uid:
                prod = self.pool.get('lunch.product').browse(cr, uid, temp['product'])
                temp['product_name'] = prod.name
                temp['date'] = temp['write_date']
                new_id = pref_ref.create(cr,uid,temp)
                result.append(new_id)
                i+=1
        return result

    def create(self, cr, uid, values, context=None):
        pref_ref = self.pool.get('lunch.preference')
        pref_ids = pref_ref.search(cr,uid,[],context=context)
        prod_ref = self.pool.get('lunch.product')
        new_id = super(lunch_order, self).create(cr, uid, values, context=context)
        already_exists = False
        if len(values['products'])>0 and values['user_id']==uid:
            for pref in pref_ref.browse(cr,uid,pref_ids,context=context):
                if pref['product'].id == values['products'][0][2]['product']:
                    if pref['note'] == values['products'][0][2]['note']:
                        if pref['price'] == values['products'][0][2]['price']:
                            already_exists = True
        if already_exists == False and len(values['products'])>0:
            new_pref = pref_ref.create(cr,uid,{'date':values['date'], 'color':0, 'order_id':new_id, 'user_id':values['user_id'], 'product':values['products'][0][2]['product'], 'product_name':prod_ref.browse(cr,uid,values['products'][0][2]['product'])['name'], 'note':values['products'][0][2]['note'], 'price':values['products'][0][2]['price']},context=context)
        return new_id
            
    def _default_preference_get(self,cr,uid,args,context=None):
        pref_ref = self.pool.get('lunch.preference')
        pref_ids = pref_ref.search(cr,uid,[],order='date desc',limit=20,context=context)
        result = []
        for pref in pref_ref.browse(cr,uid,pref_ids,context=context):
            result.append(pref.id)
        return result

    def __getattr__(self, attr):
        if attr.startswith('add_preference_'):
            pref_id = int(attr[15:])
            def specific_function(cr, uid, ids, context=None):
                return self.add_preference(cr, uid, ids, pref_id, context=context)
            return specific_function
        return super(lunch_order,self).__getattr__(self,attr)

    def fields_view_get(self, cr, uid, view_id=None, view_type=False, context=None, toolbar=False, submenu=False):
        res = super(lunch_order,self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        if view_type == 'form':
            doc = etree.XML(res['arch'])
            for sheet in doc:
                elements = sheet.xpath("//group[@name='pref']")
                for element in elements:
                    pref_ref = self.pool.get("lunch.preference")
                    pref_ids = pref_ref.search(cr,uid,[],context=context)
                    for pref in pref_ref.browse(cr,uid,pref_ids,context):
                        if pref['user_id'].id == uid:
                            function_name = "add_preference_"
                            function_name += str(pref.id)
                            new_element = etree.Element("button")
                            new_element.set('name',function_name)
                            new_element.set('icon','gtk-add')
                            new_element.set('type','object')
                            ##### title  #####
                            title = etree.Element('h3')
                            title.text = pref['product_name']
                            ##### price #####
                            price_element=etree.Element("font")
                            text = "Price: "
                            text+= str(pref['price'])
                            text+= "&#8364; "
                            price_element.text = str(text)
                            #####  note #####
                            note = etree.Element('i')
                            note.text = "Note: "+str(pref['note'])
                            #####  div  #####
                            div_element = etree.Element("group")
                            element.append(div_element)
                            div_element.append(title)
                            div_element.append(etree.Element("br"))
                            div_element.append(price_element)
                            div_element.append(etree.Element("br"))
                            div_element.append(new_element)
                            div_element.append(etree.Element("br"))
                            div_element.append(note)
                            div_element.append(etree.Element("br"))
                            div_element.append(etree.Element("br"))
                res['arch'] = etree.tostring(doc)
                return res
        return res

    _columns = {
        'user_id' : fields.many2one('res.users','User Name',required=True,readonly=True, states={'new':[('readonly', False)]}),
        'date': fields.date('Date', required=True,readonly=True, states={'new':[('readonly', False)]}),
        'products' : fields.one2many('lunch.order.line','order_id','Products',ondelete="cascade",readonly=True,states={'new':[('readonly', False)]}),
        'total' : fields.function(_price_get, string="Total",store=True),
        'state': fields.selection([('new', 'New'),('confirmed','Confirmed'), ('cancelled','Cancelled'), ('partially','Parcially Confirmed')], \
            'Status', readonly=True, select=True),
        'alerts': fields.function(_alerts_get, string="Alerts", type='text'),
        'preferences': fields.many2many("lunch.preference",'lunch_preference_rel','preferences','order_id','Preferences'),
    }

    _defaults = {
        'user_id': lambda self, cr, uid, context: uid,
        'date': fields.date.context_today,
        'state': lambda self, cr, uid, context: 'new',
        'alerts': _default_alerts_get,
        'preferences': _default_preference_get,
    }

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

class lunch_preference(osv.Model):
    _name = 'lunch.preference'
    _description= "user preferences"

    def onclick_preference(self,cr,uid,ids,context=None):
        print cr
        print uid
        print ids
        print context
        print self.pool.get('lunch.preference').browse(cr,uid,ids,context)[0]['product_name']
        return True

    _columns = {
        'date' : fields.date('Date', required=True,readonly=True),
        'color': fields.integer('Color'),
        'user_id' : fields.many2one('res.users','User Name',required=True,readonly=True),
        'product' : fields.many2one('lunch.product','Product',required=True),
        'product_name' : fields.char('Product name',size=64),
        'note' : fields.text('Note',size=256,required=False),
        'price' : fields.float('Price',digits=(16,2)),
    }

    _defaults = {      
        'color': 1,
    }

class lunch_product(osv.Model):
    """ lunch product """
    _name = 'lunch.product'
    _description = 'lunch product'
    _columns = {
        'name' : fields.char('Product',required=True, size=64),
        'category_id': fields.many2one('lunch.product.category', 'Category'),
        'description': fields.text('Description', size=256, required=False),
        'price': fields.float('Price', digits=(16,2)),
        'active': fields.boolean('Active'), #If this product isn't offered anymore, the active boolean is set to false. This will allow to keep trace of previous orders and cashmoves.
        'supplier' : fields.many2one('res.partner','Supplier',required=True, domain=[('supplier_lunch','=',True)]), 
    }

class lunch_product_category(osv.Model):
    """ lunch product category """
    _name = 'lunch.product.category'
    _description = 'lunch product category'
    _columns = {
        'name' : fields.char('Category', required=True, size=64), #such as PIZZA, SANDWICH, PASTA, CHINESE, BURGER, ...
    }

class lunch_cashmove(osv.Model):
    """ lunch cashmove => order or payment """
    _name = 'lunch.cashmove'
    _description = 'lunch cashmove'
    _columns = {
        'user_id' : fields.many2one('res.users','User Name',required=True),
        'date' : fields.date('Date', required=True),
        'amount' : fields.float('Amount', required=True), #depending on the kind of cashmove, the amount will be positive or negative
        'description' : fields.text('Description',size=256), #the description can be an order or a payment
        'order_id' : fields.many2one('lunch.order.line','Order',required=False,ondelete='cascade'),
        'state' : fields.selection([('order','Order'),('payment','Payment')],'Is an order or a Payment'),
    }
    _defaults = {
        'user_id': lambda self, cr, uid, context: uid,
        'date': fields.date.context_today,
        'state': lambda self, cr, uid, context: 'payment',
    }

class lunch_alert(osv.Model):
    """ lunch alert """
    _name = 'lunch.alert'
    _description = 'lunch alert'
    _columns = {
        'message' : fields.text('Message',size=256, required=True),
        'active' : fields.boolean('Active'),
        'day' : fields.selection([('specific','Specific day'), ('week','Every Week'), ('days','Every Day')], 'Recurrency'),
        'specific' : fields.date('Day'),
        'monday' : fields.boolean('Monday'),
        'tuesday' : fields.boolean('Tuesday'),
        'wednesday' : fields.boolean('Wednesday'),
        'thursday' : fields.boolean('Thursday'),
        'friday' : fields.boolean('Friday'),
        'saturday' : fields.boolean('Saturday'),
        'sunday' :  fields.boolean('Sunday'),
        'active_from': fields.float('Between',required=True),
        'active_to': fields.float('And',required=True),
    }

class lunch_cancel(osv.Model):
    """ lunch cancel """
    _name = 'lunch.cancel'
    _description = 'cancel lunch order'

    def cancel(self,cr,uid,ids,context=None):
        #confirm one or more order.line, update order status and create new cashmove
        cashmove_ref = self.pool.get('lunch.cashmove')
        order_lines_ref = self.pool.get('lunch.order.line')
        orders_ref = self.pool.get('lunch.order')
        order_ids = context.get('active_ids', [])

        for order in order_lines_ref.browse(cr,uid,order_ids,context=context):
            order_lines_ref.write(cr,uid,[order.id],{'state':'cancelled'},context)
            for cash in order.cashmove:
                cashmove_ref.unlink(cr,uid,cash.id,context)
        for order in order_lines_ref.browse(cr,uid,order_ids,context=context):
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

class lunch_validation(osv.Model):
    """ lunch validation """
    _name = 'lunch.validation'
    _description = 'lunch validation for order'

    def confirm(self,cr,uid,ids,context=None):
        #confirm one or more order.line, update order status and create new cashmove
        cashmove_ref = self.pool.get('lunch.cashmove')
        order_lines_ref = self.pool.get('lunch.order.line')
        orders_ref = self.pool.get('lunch.order')
        order_ids = context.get('active_ids', [])

        for order in order_lines_ref.browse(cr,uid,order_ids,context=context):
            if order.state!='confirmed':
                new_id = cashmove_ref.create(cr,uid,{'user_id': order.user_id.id, 'amount':0 - order.price,'description':order.product.name, 'order_id':order.id, 'state':'order', 'date':order.date})
                order_lines_ref.write(cr,uid,[order.id],{'cashmove':[('0',new_id)], 'state':'confirmed'},context)
        for order in order_lines_ref.browse(cr,uid,order_ids,context=context):
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
        