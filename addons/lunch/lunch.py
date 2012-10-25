
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
import addons #TODO: not needed
import tools #TODO: currently not needed, but you may want to import _ from tools.translte
import pytz
import time
from osv import osv, fields
from datetime import datetime, timedelta
from lxml import etree

#TODO: try to space more your code for a batter readability (follow PEP8 standards for coding layout is nice (except 80 characters max per line which is outdated))
#  -  def _price_get(self,cr,uid,ids,name,arg,context=None):
#  +  def _price_get(self, cr, uid, ids, name, arg, context=None):

#TODO: add some docstrings on methods when it is needed

class lunch_order(osv.Model):
    """ lunch order """
    _name = 'lunch.order'
    _description = 'Lunch Order'

    def _price_get(self, cr, uid, ids, name, arg, context=None):
        #TODO: `orders´ variable is not needed. You can use `for x in self.browse(...):´
        orders = self.browse(cr, uid, ids, context=context)
        result={}
        for order in orders:
            value = 0.0
            for product in order.products: #TODO: use meaningful variable names `for order_line in ...´
                if product.state != 'cancelled':
                    value+=product.product.price
                    result[order.id]=value
        return result

    def add_preference(self,cr,uid,ids,pref_id,context=None):
        #TODO: docstring
        pref_ref = self.pool.get("lunch.preference")
        orderline_ref = self.pool.get('lunch.order.line')
        order = self.browse(cr,uid,ids,context=context)[0]
        pref = pref_ref.browse(cr,uid,pref_id,context=context)
        #TODO: get your information on browse_record objects by using `.´ instead of `[]´. 
        #  e.g: `pref.user_id.id == uid´ instead of `pref['user_id'].id´
        prod_ref = self.pool.get('lunch.product') #TODO: usually, all the statements for `self.pool.get(...)´ are grouped at the beginning of the method
        if pref["user_id"].id == uid: #TODO: i don't get the meaning of this line...
            #TODO: new_order_line = {
            #          'date': order.date,
            #          ...
            #      }
            new_order_line = {}
            new_order_line['date'] = order["date"]
            new_order_line['user_id'] = uid
            new_order_line['product'] = pref["product"].id
            new_order_line['note'] = pref["note"]
            new_order_line['order_id'] = order.id
            new_order_line['price'] = pref["price"]
            new_order_line['supplier'] = prod_ref.browse(cr,uid,pref["product"].id,context=context)['supplier'].id
            new_id = orderline_ref.create(cr,uid,new_order_line)#TODO: add missing `context´ arg
            order.products.append(new_id)
            #TODO: total is a computed field, so the write is useless, no?
            total = self._price_get(cr,uid,ids," "," ",context=context)
            self.write(cr,uid,ids,{'total':total},context) 
        return True

    def _alerts_get(self,cr,uid,ids,name,arg,context=None):
        orders = self.browse(cr,uid,ids,context=context)
        alert_ref = self.pool.get('lunch.alert')
        alert_ids = alert_ref.search(cr,uid,[],context=context) #TODO: not used
        result={}
        alert_msg= self._default_alerts_get(cr,uid,arg,context)
        for order in orders:
            if order.state=='new':
                result[order.id]=alert_msg
        return result

    def check_day(self,alert):
        #TODO: docstring
        today = datetime.now().isoweekday()
        if today == 1:
            if alert.monday == True:
                return True
        if today == 2:
            if alert.tuesday == True:
                return True
        if today == 3:
            if alert.wednesday == True:
                return True
        if today == 4:
            if alert.thursday == True:
                return True
        if today == 5:
            if alert.friday == True:
                return True
        if today == 6:
            if alert.saturday == True:
                return True
        if today == 7:
            if alert.sunday == True:
                return True
        return False

    def _default_alerts_get(self,cr,uid,arg,context=None):
        #TODO: docstring
        alert_ref = self.pool.get('lunch.alert')
        alert_ids = alert_ref.search(cr,uid,[('active','=',True)],context=context) #TODO: active=True is automatically added by orm, so this param can be removed
        alert_msg=""
        for alert in alert_ref.browse(cr,uid,alert_ids,context=context):
            if alert : #TODO useless `if´ statement
                #there are alerts
                display = False #TODO: should refactor in order to check if there is an alert in one function. Then use `if self.check_alert():...´
                if alert.day=='specific':
                    #the alert is only activated a specific day
                    if alert.specific==fields.datetime.now().split(' ')[0]:
                        display = True
                elif alert.day=='week':
                    #the alert is activated during some days of the week
                    display = self.check_day(alert)
                elif alert.day=='days':
                    #the alert is activated everyday
                    display = True
                #Check if we can display the alert
                if display == True:
                    if alert.active_from==alert.active_to:
                        #the alert is executing all the day
                        alert_msg+="* "
                        alert_msg+=alert.message
                        alert_msg+='\n'
                    elif alert.active_from<alert.active_to:
                        #TODO: this part seems overcomplicated, so i skipped it for now :-)
                        #the alert is executing from ... to ...
                        now = datetime.utcnow()
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
                #TODO: that's weird. should truy to find another way to compute total on order lines when record is not saved...
                #   or at least put some comments
                if isinstance(prod[1],bool): 
                    orderline = prod[2]
                    tot += orderline['price']
                else:
                    orderline = self.pool.get('lunch.order.line').browse(cr,uid,prod[1],context=context)
                    tot += orderline.price
                res = {'value':{'total':tot}} #TODO: should be outside the loop
        return res

    def create(self, cr, uid, values, context=None):
        pref_ref = self.pool.get('lunch.preference')
        pref_ids = pref_ref.search(cr,uid,[],context=context)
        prod_ref = self.pool.get('lunch.product')
        new_id = super(lunch_order, self).create(cr, uid, values, context=context)
        already_exists = False #TODO: what's that trick with already_exists?? it's weird.
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
        pref_ids = pref_ref.search(cr,uid,[('user_id','=',uid)],order='date desc',limit=15,context=context)
        #TODO: heeeuu... return pref_ids ?
        result = []
        for pref in pref_ref.browse(cr,uid,pref_ids,context=context):
            result.append(pref.id)
        return result

    def __getattr__(self, attr):
        #TODO: not reviewed
        if attr.startswith('add_preference_'):
            pref_id = int(attr[15:])
            def specific_function(cr, uid, ids, context=None):
                return self.add_preference(cr, uid, ids, pref_id, context=context)
            return specific_function
        return super(lunch_order,self).__getattr__(self,attr)

    def fields_view_get(self, cr, uid, view_id=None, view_type=False, context=None, toolbar=False, submenu=False):
        #TODO: not reviewed
        res = super(lunch_order,self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        if view_type == 'form':
            pref_ref = self.pool.get("lunch.preference")
            pref_ids = pref_ref.search(cr,uid,[('user_id','=',uid)],context=context)
            prod_ref = self.pool.get("lunch.product")
            preferences = pref_ref.browse(cr,uid,pref_ids,context=context)
            categories = {} #store the different categories of products in preference
            for pref in preferences:
                categories[pref['product']['category_id']['name']]=[]
            for pref in preferences:
                categories[pref['product']['category_id']['name']].append(pref)
            length = len(categories)
            text_xml = ""
            for key,value in categories.items():
                text_xml+= ('''
                    <div style=\"width: 33%; display: inline-block;\">
                    <h1>
                ''')+str(key)+('''
                    </h1>
                ''')
                for val in value:
                    function_name = "add_preference_"+str(val.id)
                    text_xml+= ('''
                        <div class=\"vignette\">
                    ''')+val['product_name']+('''
                        <span class=\"oe_tag\">
                    ''')+str(val['price'])+('''
                        </span>
                        <span class=\"oe_note\">
                    ''')+val['note']+('''
                        </span>
                        <button class='oe_button' name="''')+function_name+('''" type="object" icon="gtk-add"/>
                        </div>
                    ''')
                text_xml+= (''' </div> ''')
            res['arch'] = ('''<form string=\"Orders Form\" version=\"7.0\">
                <header>
                    <field name=\"state\" widget=\"statusbar\" statusbar_visible=\"new,confirmed\" modifiers=\"{&quot;readonly&quot;: true}\"/>
                </header>
                <sheet>
                    <group>
                        <group>
                            <field name=\"user_id\" modifiers=\"{&quot;readonly&quot;: [[&quot;state&quot;, &quot;not in&quot;, [&quot;new&quot;]]], &quot;required&quot;: true}\"/>
                        </group>
                        <group> 
                            <field name=\"date\" modifiers=\"{&quot;readonly&quot;: [[&quot;state&quot;, &quot;not in&quot;, [&quot;new&quot;]]], &quot;required&quot;: true}\"/>
                        </group>
                    </group>
                    <img src=\"/lunch/static/src/img/warning.png\" width=\"30\" height=\"30\" class=\"oe_left oe_avatar\" attrs=\"{'invisible': [('state','!=','new')]}\" modifiers=\"{&quot;invisible&quot;: [[&quot;state&quot;, &quot;!=&quot;, &quot;new&quot;]]}\"/>
                    <div class=\"oe_title\">
                        <field name=\"alerts\" attrs=\"{'invisible': [('state','!=','new')]}\" modifiers=\"{&quot;invisible&quot;: [[&quot;state&quot;, &quot;!=&quot;, &quot;new&quot;]], &quot;readonly&quot;: true}\"/> 
                    </div>
                    <separator name=\"pref\" string=\"Quick Select a Product\"/>
                    '''+text_xml+'''
                    <separator string=\"Select Products\"/>
                    <field name=\"products\" colspan=\"4\" nolabel=\"1\" on_change=\"onchange_price(products)\" modifiers=\"{&quot;readonly&quot;: [[&quot;state&quot;, &quot;not in&quot;, [&quot;new&quot;]]]}\">
                        </field> 
                    <group class=\"oe_subtotal_footer oe_right\">
                        <field name=\"total\" modifiers=\"{&quot;readonly&quot;: true}\"/>
                    </group>
                    <br/><br/>
                </sheet>
            </form>''')
        return res

    _columns = {
        'user_id' : fields.many2one('res.users','User Name',required=True,readonly=True, states={'new':[('readonly', False)]}),
        'date': fields.date('Date', required=True,readonly=True, states={'new':[('readonly', False)]}),
        'products' : fields.one2many('lunch.order.line','order_id','Products',ondelete="cascade",readonly=True,states={'new':[('readonly', False)]}), #TODO: a good naming convention is to finish your field names with `_ids´ for *2many fields. BTW, the field name should reflect more it's nature: `order_line_ids´ for example
        'total' : fields.function(_price_get, string="Total",store=True),
        'state': fields.selection([('new', 'New'),('confirmed','Confirmed'), ('cancelled','Cancelled'), ('partially','Parcially Confirmed')], \ 
            'Status', readonly=True, select=True), #TODO: parcially? #TODO: the labels are confusing. confirmed=='received' or 'delivered'...
        'alerts': fields.function(_alerts_get, string="Alerts", type='text'),
        'preferences': fields.many2many("lunch.preference",'lunch_preference_rel','preferences','order_id','Preferences'), #TODO: preference_ids
    }

    _defaults = {
        'user_id': lambda self, cr, uid, context: uid,
        'date': fields.date.context_today,
        'state': lambda self, cr, uid, context: 'new', #TODO: remove the lambda()
        'alerts': _default_alerts_get,
        'preferences': _default_preference_get,
    }

class lunch_order_line(osv.Model): #define each product that will be in one ORDER.#TODO :D do not put comments because i said so, but because it's needed ^^
    """ lunch order line """
    _name = 'lunch.order.line'
    _description = 'lunch order line'

    def _price_get(self,cr,uid,ids,name,arg,context=None):
        orderLines = self.browse(cr,uid,ids,context=context)
        result={}
        for orderLine in orderLines: #TODO: get rid of `orderLines´ variable #TODO: usually, we don't use the CamelCase notation. For a better consistency you should use `order_line´
            result[orderLine.id]=orderLine.product.price
        return result

    def onchange_price(self,cr,uid,ids,product,context=None):
        if product:
            price = self.pool.get('lunch.product').read(cr, uid, product, ['price'])['price']#TODO: pass `context´ in args or read()
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
        #TODO: how can this be working??? self is 'lunch.order.line' object, not 'lunch.order'... refactor
        for order in self.browse(cr,uid,ids,context=context):
            isconfirmed = True
            for product in order.order_id.products:
                if product.state == 'new':
                    isconfirmed = False
                if product.state == 'cancelled':
                    isconfirmed = False
                    orders_ref.write(cr,uid,[order.order_id.id],{'state':'partially'},context)
            if isconfirmed == True:
                orders_ref.write(cr,uid,[order.order_id.id],{'state':'confirmed'},context) #TODO: context is a kwarg
        return {}

    def cancel(self,cr,uid,ids,context=None):
        #confirm one or more order.line, update order status and create new cashmove
        cashmove_ref = self.pool.get('lunch.cashmove')
        orders_ref = self.pool.get('lunch.order')

        #TODO: how can this be working??? self is 'lunch.order.line' object, not 'lunch.order'... refactor
        for order in self.browse(cr,uid,ids,context=context):
            self.write(cr,uid,[order.id],{'state':'cancelled'},context)
            for cash in order.cashmove:
                cashmove_ref.unlink(cr,uid,cash.id,context)
        #TODO: how can this be working??? self is 'lunch.order.line' object, not 'lunch.order'... refactor
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
        'date' : fields.related('order_id','date',type='date', string="Date", readonly=True,store=True), #TODO: where is it used?
        'supplier' : fields.related('product','supplier',type='many2one',relation='res.partner',string="Supplier",readonly=True,store=True),#TODO: where is it used?
        'user_id' : fields.related('order_id', 'user_id', type='many2one', relation='res.users', string='User', readonly=True, store=True),#TODO: where is it used?
        'product' : fields.many2one('lunch.product','Product',required=True), #one offer can have more than one product and one product can be in more than one offer
            #TODO remove wrong (what's an `offer´?) and useless comment (people knows what's a many2one)
        'note' : fields.text('Note',size=256,required=False),#TODO: required is False by default. Can be removed
        'order_id' : fields.many2one('lunch.order','Order',ondelete='cascade'), #TODO: this one should be required=True
        'price' : fields.function(_price_get, string="Price",store=True), #TODO: isn't it a fields.related?
        'state': fields.selection([('new', 'New'),('confirmed','Confirmed'), ('cancelled','Cancelled')], \
            'Status', readonly=True, select=True), #TODO: labels are confusing. Should be: 'ordered', 'received' or 'not received'
        'cashmove': fields.one2many('lunch.cashmove','order_id','Cash Move',ondelete='cascade'),
        
    }
    _defaults = {
        #TODO: remove lambda()
        'state': lambda self, cr, uid, context: 'new',        
    }

class lunch_preference(osv.Model):
#TODO: class not reviewed yet
    _name = 'lunch.preference'
    _description= "user preferences"

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
#TODO: class not reviewed yet
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
#TODO: class not reviewed yet
    """ lunch product category """
    _name = 'lunch.product.category'
    _description = 'lunch product category'
    _columns = {
        'name' : fields.char('Category', required=True, size=64), #such as PIZZA, SANDWICH, PASTA, CHINESE, BURGER, ...
    }

class lunch_cashmove(osv.Model):
#TODO: class not reviewed yet
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
#TODO: class not reviewed yet
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
#TODO: class not reviewed yet
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
#TODO: class not reviewed yet
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
