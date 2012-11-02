
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

from xml.sax.saxutils import escape
import pytz
import time
from osv import osv, fields
from datetime import datetime, timedelta
from lxml import etree
from tools.translate import _

class lunch_order(osv.Model):
    """ lunch order """
    _name = 'lunch.order'
    _description = 'Lunch Order'

    def _price_get(self, cr, uid, ids, name, arg, context=None):
        """ get and sum the order lines' price"""
        result={}
        for order in self.browse(cr, uid, ids, context=context):
            value = 0.0
            for orderline in order.order_line_ids:
                value += orderline.product_id.price
                result[order.id]=value
        return result

    def _compute_total(self, cr, uid, ids, name, context=None):
        """ compute total"""
        result=  {}
        for order_line in self.browse(cr, uid, ids, context=context):
            result[order_line.order_id.id] = True
        return result.keys()

    def add_preference(self, cr, uid, ids, pref_id, context=None):
        """ create a new order line based on the preference selected (pref_id)"""
        orderline_ref = self.pool.get('lunch.order.line')
        prod_ref = self.pool.get('lunch.product')
        order = self.browse(cr,uid,ids,context=context)[0]
        pref = orderline_ref.browse(cr,uid,pref_id,context=context)
        new_order_line = {
            'date': order.date,
            'user_id': uid,
            'product_id': pref.product_id.id,
            'note': pref.note,
            'order_id': order.id,
            'price': pref.product_id.price,
            'supplier': pref.product_id.supplier.id
        }
        return orderline_ref.create(cr,uid,new_order_line)

    def _alerts_get(self, cr, uid, ids, name, arg, context=None):
        """ get the alerts to display on the order form """
        orders = self.browse(cr,uid,ids,context=context)
        result={}
        alert_msg= self._default_alerts_get(cr,uid,arg,context=context)
        for order in orders:
            if order.state=='new':
                result[order.id]=alert_msg
        return result

    def check_day(self, alert):
        """ This method is used by can_display_alert to
            to check if the alert day corresponds
            to the current day 
        """
        today = datetime.now().isoweekday()
        if today == 1:
            return alert.monday
        if today == 2:
            return alert.tuesday
        if today == 3:
            return alert.wednesday
        if today == 4:
            return alert.thursday
        if today == 5:
            return alert.friday
        if today == 6:
            return alert.saturday
        if today == 7:
            return alert.sunday
        assert "today should be between 1 and 7"

    def can_display_alert(self, alert):
        """ This method check if the alert can be displayed today """
        if alert.day=='specific':
            #the alert is only activated a specific day
            return alert.specific==fields.datetime.now()[:10]
        elif alert.day=='week':
            #the alert is activated during some days of the week
            return self.check_day(alert)
        return True

    # code to improve
    def _default_alerts_get(self,cr,uid,arg,context=None):
        """ get the alerts to display on the order form """
        alert_ref = self.pool.get('lunch.alert')
        alert_ids = alert_ref.search(cr,uid,[],context=context) 
        alert_msg = []
        for alert in alert_ref.browse(cr,uid,alert_ids,context=context):
            if self.can_display_alert(alert):
                #the alert is executing from ... to ...
                now = datetime.utcnow()
                user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
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
                    alert_msg.append(alert.message)
        return '\n'.join(alert_msg)

    def onchange_price(self,cr,uid,ids,order_line_ids,context=None):
        """ Onchange methode that refresh the total price of order"""
        res = {'value':{'total':0.0}}
        order_line_ids= self.resolve_o2m_commands_to_record_dicts(cr, uid, "order_line_ids", order_line_ids, ["price"], context)
        if order_line_ids:
            tot = 0.0
            product_ref = self.pool.get("lunch.product")
            for prod in order_line_ids:
                if 'product_id' in prod:
                    tot += product_ref.browse(cr,uid,prod['product_id'],context=context).price
                else:
                    tot += prod['price']
            res = {'value':{'total':tot}}
        return res

    def __getattr__(self, attr):
        """ this method catch unexisting method call and if starts with
            add_preference_'n' we execute the add_preference method with 
            'n' as parameter """
        if attr.startswith('add_preference_'):
            pref_id = int(attr[15:])
            def specific_function(cr, uid, ids, context=None):
                return self.add_preference(cr, uid, ids, pref_id, context=context)
            return specific_function
        return super(lunch_order,self).__getattr__(self,attr)

    def fields_view_get(self, cr, uid, view_id=None, view_type=False, context=None, toolbar=False, submenu=False):
        """ Add preferences in the form view of order.line """
        res = super(lunch_order,self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        line_ref = self.pool.get("lunch.order.line")
        if view_type == 'form':
            pref_ids = line_ref.search(cr,uid,[('user_id','=',uid)],context=context)
            text_xml = "<div>"
            if len(pref_ids)==0:
                text_xml+="""
                    <div class="oe_inline oe_lunch_intro">
                        <h3>%s</h3>
                        <p class="oe_grey">
                        %s
                        </p><p class="oe_grey">
                        %s
                        </p><p class="oe_grey">
                        %s
                        </p>
                    </div>
                    """ % (_("This is the first time you order a meal"),
                            _("Select a product and put your order comments on the note."),
                            _("Your favorite meals will be created based on your last orders."),
                            _("Don't forget the alerts displayed in the reddish area"))
            else:
                preferences = line_ref.browse(cr,uid,pref_ids,context=context)
                categories = {} #store the different categories of products in preference
                for pref in preferences:
                    categories.setdefault(pref.product_id.category_id.name, {})
                    if pref.product_id.id not in categories[pref.product_id.category_id.name]:
                        categories[pref.product_id.category_id.name][pref.product_id.id] = pref

                currency = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.currency_id

                for key,value in categories.items():
                    value = value.values()
                    text_xml+="""
                    <div class="oe_lunch_30pc">
                    <h2>%s</h2>
                    """ % (key,)
                    i = 0
                    for val in value:
                        if i==5 : break
                        i+=1
                        function_name = "add_preference_"+str(val.id)
                        text_xml+= '''
                            <div class="oe_lunch_vignette">
                                <span class="oe_lunch_button">
                                    <button name="%s" class="oe_link oe_i oe_button_plus" type="object" string="+"></button><button name="%s" class="oe_link oe_button_add" type="object" string="%s"></button>
                                </span>
                                <div class="oe_group_text_button">
                                   <div class="oe_lunch_text">
                                       %s
                                       <span class="oe_tag">%.2f %s</span>
                                   </div>
                                </div>
                                <div class="oe_grey">
                                    %s
                                </div>
                            </div>
                        ''' % (function_name, function_name,_("Add"), escape(val.product_id.name), val.product_id.price or 0.0, currency.name or '', escape(val.note or ''))
                    text_xml+= '''</div>'''
            # ADD into ARCH xml
            text_xml += "</div>"
            doc = etree.XML(res['arch'])
            node = doc.xpath("//div[@name='preferences']")
            to_add = etree.fromstring(text_xml)
            node[0].append(to_add)
            res['arch'] = etree.tostring(doc)
        return res

    _columns = {
        'user_id' : fields.many2one('res.users','User Name',required=True,readonly=True, states={'new':[('readonly', False)]}),
        'date': fields.date('Date', required=True,readonly=True, states={'new':[('readonly', False)]}),
        'order_line_ids' : fields.one2many('lunch.order.line','order_id','Products',ondelete="cascade",readonly=True,states={'new':[('readonly', False)]}), #TODO: a good naming convention is to finish your field names with `_ids´ for *2many fields. BTW, the field name should reflect more it's nature: `order_line_ids´ for example
        'total' : fields.function(_price_get, string="Total",store={
                 'lunch.order.line': (_compute_total, ['product_id','order_id'], 20),
            }),
        'state': fields.selection([('new', 'New'),('confirmed','Confirmed'), ('cancelled','Cancelled'), ('partially','Partially Confirmed')],'Status', readonly=True, select=True), #TODO: parcially? #TODO: the labels are confusing. confirmed=='received' or 'delivered'...
        'alerts': fields.function(_alerts_get, string="Alerts", type='text'),
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'currency_id': fields.related('company_id','currency_id',string="Currency", readonly=True),
    }

    _defaults = {
        'user_id': lambda self, cr, uid, context: uid,
        'date': fields.date.context_today,
        'state': 'new',
        'alerts': _default_alerts_get,
        'company_id': lambda self,cr,uid,context: self.pool.get('res.company')._company_default_get(cr, uid, 'lunch.order', context=context),
    }


class lunch_order_line(osv.Model):
    """ lunch order line : one lunch order can have many order lines"""
    _name = 'lunch.order.line'
    _description = 'lunch order line'

    def onchange_price(self,cr,uid,ids,product_id,context=None):
        if product_id:
            price = self.pool.get('lunch.product').read(cr, uid, product_id, ['price'])['price']
            return {'value': {'price': price}}
        return {'value': {'price': 0.0}}

    def order(self,cr,uid,ids,context=None):
        for order_line in self.browse(cr,uid,ids,context=context):
            self.write(cr,uid,[order_line.id],{'state':'ordered'},context)
        return {}

    def confirm(self,cr,uid,ids,context=None):
        """ confirm one or more order line, update order status and create new cashmove """
        cashmove_ref = self.pool.get('lunch.cashmove')
        for order_line in self.browse(cr,uid,ids,context=context):
            if order_line.state!='confirmed':
                new_id = cashmove_ref.create(cr,uid,{'user_id': order_line.user_id.id, 'amount':-order_line.price,'description':order_line.product_id.name, 'order_id':order_line.id, 'state':'order', 'date':order_line.date})
                self.write(cr,uid,[order_line.id],{'state':'confirmed'},context)
        return self._update_order_lines(cr, uid, ids, context)

    def _update_order_lines(self, cr, uid, ids, context=None):
        orders_ref = self.pool.get('lunch.order')
        orders = []
        for order_line in self.browse(cr,uid,ids,context=context):
            orders.append(order_line.order_id)
        for order in set(orders):
            isconfirmed = True
            for orderline in order.order_line_ids:
                if orderline.state == 'new':
                    isconfirmed = False
                if orderline.state == 'cancelled':
                    isconfirmed = False
                    orders_ref.write(cr,uid,[order.id],{'state':'partially'},context=context)
            if isconfirmed:
                orders_ref.write(cr,uid,[order.id],{'state':'confirmed'},context=context)
        return {}

    def cancel(self,cr,uid,ids,context=None):
        """ confirm one or more order.line, update order status and create new cashmove """
        cashmove_ref = self.pool.get('lunch.cashmove')
        for order_line in self.browse(cr,uid,ids,context=context):
            self.write(cr,uid,[order_line.id],{'state':'cancelled'},context)
            for cash in order_line.cashmove:
                cashmove_ref.unlink(cr,uid,cash.id,context)
        return self._update_order_lines(cr, uid, ids, context)

    _columns = {
        'name' : fields.related('product_id','name',readonly=True),
        'order_id' : fields.many2one('lunch.order','Order',ondelete='cascade'),
        'product_id' : fields.many2one('lunch.product','Product',required=True), 
        'date' : fields.related('order_id','date',type='date', string="Date", readonly=True,store=True),
        'supplier' : fields.related('product_id','supplier',type='many2one',relation='res.partner',string="Supplier",readonly=True,store=True),
        'user_id' : fields.related('order_id', 'user_id', type='many2one', relation='res.users', string='User', readonly=True, store=True),
        'note' : fields.text('Note',size=256,required=False),
        'price' : fields.float("Price"),
        'state': fields.selection([('new', 'New'),('confirmed','Received'), ('ordered','Ordered'), ('cancelled','Cancelled')], \
            'Status', readonly=True, select=True), #new confirmed and cancelled are the convention
        'cashmove': fields.one2many('lunch.cashmove','order_id','Cash Move',ondelete='cascade'),
        
    }
    _defaults = {
        'state': 'new',
    }


class lunch_product(osv.Model):
    """ lunch product """
    _name = 'lunch.product'
    _description = 'lunch product'
    _columns = {
        'name' : fields.char('Product',required=True, size=64),
        'category_id': fields.many2one('lunch.product.category', 'Category', required=True),
        'description': fields.text('Description', size=256, required=False),
        'price': fields.float('Price', digits=(16,2)),
        'supplier' : fields.many2one('res.partner', 'Supplier'), 
    }

class lunch_product_category(osv.Model):
    """ lunch product category """
    _name = 'lunch.product.category'
    _description = 'lunch product category'
    _columns = {
        'name' : fields.char('Category', required=True), #such as PIZZA, SANDWICH, PASTA, CHINESE, BURGER, ...
    }

class lunch_cashmove(osv.Model):
    """ lunch cashmove => order or payment """
    _name = 'lunch.cashmove'
    _description = 'lunch cashmove'
    _columns = {
        'user_id' : fields.many2one('res.users','User Name',required=True),
        'date' : fields.date('Date', required=True),
        'amount' : fields.float('Amount', required=True), #depending on the kind of cashmove, the amount will be positive or negative
        'description' : fields.text('Description'), #the description can be an order or a payment
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
        'day' : fields.selection([('specific','Specific day'), ('week','Every Week'), ('days','Every Day')], string='Recurrency', required=True,select=True),
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
    _defaults = {
        'day': lambda self, cr, uid, context: 'specific',
        'specific': lambda self, cr, uid, context: time.strftime('%Y-%m-%d'),
        'active_from': 7,
        'active_to': 23,
    }