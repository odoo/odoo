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

import time
from openerp.osv import fields, osv
from datetime import datetime
from openerp import tools
from openerp.tools.translate import _

class lunch_order(osv.Model):
    """ 
    lunch order (contains one or more lunch order line(s))
    """
    _name = 'lunch.order'
    _description = 'Lunch Order'
    _order = 'date desc'

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        res = []
        for elmt in self.browse(cr, uid, ids, context=context):
            name = _("Lunch Order")
            name = name + ' ' + str(elmt.id)
            res.append((elmt.id, name))
        return res
        
    def _price_get(self, cr, uid, ids, name, arg, context=None):
        """ 
        get and sum the order lines' price
        """
        result = dict.fromkeys(ids, 0)
        for order in self.browse(cr, uid, ids, context=context):
            result[order.id] = sum(order_line.product_id.price
                                   for order_line in order.order_line_ids)
        return result

    def _fetch_orders_from_lines(self, cr, uid, ids, name, context=None):
        """ 
        return the list of lunch orders to which belong the order lines `ids´
        """
        result = set()
        for order_line in self.browse(cr, uid, ids, context=context):
            if order_line.order_id:
                result.add(order_line.order_id.id)
        return list(result)

    def _alerts_get(self, cr, uid, ids, name, arg, context=None):
        """ 
        get the alerts to display on the order form 
        """
        result = {}
        alert_msg = self._default_alerts_get(cr, uid, context=context)
        for order in self.browse(cr, uid, ids, context=context):
            if order.state == 'new':
                result[order.id] = alert_msg
        return result

    def check_day(self, alert):
        """ 
        This method is used by can_display_alert
        to check if the alert day corresponds
        to the current day 
        """
        today = datetime.now().isoweekday()
        assert 1 <= today <= 7, "Should be between 1 and 7"
        mapping = dict((idx, name) for idx, name in enumerate('days monday tuesday wednesday thursday friday saturday sunday'.split()))
        return alert[mapping[today]]

    def can_display_alert(self, alert):
        """ 
        This method check if the alert can be displayed today
        """
        if alert.alter_type == 'specific':
            #the alert is only activated on a specific day
            return alert.specific_day == time.strftime(tools.DEFAULT_SERVER_DATE_FORMAT)
        elif alert.alter_type == 'week':
            #the alert is activated during some days of the week
            return self.check_day(alert)
        return True # alter_type == 'days' (every day)

    def _default_alerts_get(self, cr, uid, context=None):
        """ 
        get the alerts to display on the order form
        """
        alert_ref = self.pool.get('lunch.alert')
        alert_ids = alert_ref.search(cr, uid, [], context=context)
        alert_msg = []
        for alert in alert_ref.browse(cr, uid, alert_ids, context=context):
            #check if the address must be displayed today
            if self.can_display_alert(alert):
                #display the address only during its active time
                mynow = fields.datetime.context_timestamp(cr, uid, datetime.now(), context=context)
                hour_to = int(alert.active_to)
                min_to = int((alert.active_to - hour_to) * 60)
                to_alert = datetime.strptime(str(hour_to) + ":" + str(min_to), "%H:%M")
                hour_from = int(alert.active_from)
                min_from = int((alert.active_from - hour_from) * 60)
                from_alert = datetime.strptime(str(hour_from) + ":" + str(min_from), "%H:%M")
                if mynow.time() >= from_alert.time() and mynow.time() <= to_alert.time():
                    alert_msg.append(alert.message)
        return '\n'.join(alert_msg)

    def _get_lunch_order_detail(self, cr, uid, ids, name, arg, context=None):
        """
        get the previous lunch order details to display on the order form
        """
        data = self._default_get_lunch_order_detail(cr, uid, context=None)
        res = {}
        for id in ids:
            res[id] = data
        return res

    def _default_get_lunch_order_detail(self, cr, uid, context=None):
        pref_ids = self.pool.get("lunch.order.line").search(cr, uid, [('user_id', '=', uid)], order='id desc', context=context)
        return pref_ids

    def onchange_price(self, cr, uid, ids, order_line_ids, context=None):
        """
        Onchange methode that refresh the total price of order
        """
        res = {'value': {'total': 0.0}}
        order_line_ids = self.resolve_o2m_commands_to_record_dicts(cr, uid, "order_line_ids", order_line_ids, ["price"], context=context)
        if order_line_ids:
            tot = 0.0
            product_ref = self.pool.get("lunch.product")
            for prod in order_line_ids:
                if 'product_id' in prod:
                    tot += product_ref.browse(cr, uid, prod['product_id'], context=context).price
                else:
                    tot += prod['price']
            res = {'value': {'total': tot}}
        return res


    _columns = {
        'user_id': fields.many2one('res.users', 'User Name', required=True, readonly=True, states={'new':[('readonly', False)]}),
        'date': fields.date('Date', required=True, readonly=True, states={'new':[('readonly', False)]}),
        'order_line_ids': fields.one2many('lunch.order.line', 'order_id', 'Products',
                                          ondelete="cascade", readonly=True, states={'new':[('readonly', False)]},
                                          copy=True),
        'total': fields.function(_price_get, string="Total", store={
                 'lunch.order.line': (_fetch_orders_from_lines, ['product_id','order_id'], 20),
            }),
        'state': fields.selection([('new', 'New'), \
                                    ('confirmed','Confirmed'), \
                                    ('cancelled','Cancelled'), \
                                    ('partially','Partially Confirmed')] \
                                ,'Status', readonly=True, select=True, copy=False),
        'alerts': fields.function(_alerts_get, string="Alerts", type='text'),
        'previous_order_details': fields.function(_get_lunch_order_detail, string="Previous Orders", type='one2many', relation="lunch.order.line"),
    }

    _defaults = {
        'user_id': lambda self, cr, uid, context: uid,
        'date': fields.date.context_today,
        'state': 'new',
        'alerts': _default_alerts_get,
        'previous_order_details': _default_get_lunch_order_detail,
    }


class lunch_order_line(osv.Model):
    """ 
    lunch order line: one lunch order can have many order lines
    """
    _name = 'lunch.order.line'
    _description = 'lunch order line'

    def onchange_price(self, cr, uid, ids, product_id, context=None):
        if product_id:
            price = self.pool.get('lunch.product').browse(cr, uid, product_id, context=context).price
            return {'value': {'price': price}}
        return {'value': {'price': 0.0}}

    def order(self, cr, uid, ids, context=None):
        """ 
        The order_line is ordered to the supplier but isn't received yet
        """
        self.write(cr, uid, ids, {'state': 'ordered'}, context=context)
        return self._update_order_lines(cr, uid, ids, context=context)

    def confirm(self, cr, uid, ids, context=None):
        """ 
        confirm one or more order line, update order status and create new cashmove 
        """
        cashmove_ref = self.pool.get('lunch.cashmove')
        for order_line in self.browse(cr, uid, ids, context=context):
            if order_line.state != 'confirmed':
                values = {
                    'user_id': order_line.user_id.id,
                    'amount': -order_line.price,
                    'description': order_line.product_id.name,
                    'order_id': order_line.id,
                    'state': 'order',
                    'date': order_line.date,
                }
                cashmove_ref.create(cr, uid, values, context=context)
                order_line.write({'state': 'confirmed'})
        return self._update_order_lines(cr, uid, ids, context=context)

    def _update_order_lines(self, cr, uid, ids, context=None):
        """
        Update the state of lunch.order based on its orderlines
        """
        orders_ref = self.pool.get('lunch.order')
        orders = []
        for order_line in self.browse(cr, uid, ids, context=context):
            orders.append(order_line.order_id)
        for order in set(orders):
            isconfirmed = True
            for orderline in order.order_line_ids:
                if orderline.state == 'new':
                    isconfirmed = False
                if orderline.state == 'cancelled':
                    isconfirmed = False
                    orders_ref.write(cr, uid, [order.id], {'state': 'partially'}, context=context)
            if isconfirmed:
                orders_ref.write(cr, uid, [order.id], {'state': 'confirmed'}, context=context)
        return {}

    def cancel(self, cr, uid, ids, context=None):
        """
        cancel one or more order.line, update order status and unlink existing cashmoves
        """
        cashmove_ref = self.pool.get('lunch.cashmove')
        self.write(cr, uid, ids, {'state':'cancelled'}, context=context)
        for order_line in self.browse(cr, uid, ids, context=context):
            cash_ids = [cash.id for cash in order_line.cashmove]
            cashmove_ref.unlink(cr, uid, cash_ids, context=context)
        return self._update_order_lines(cr, uid, ids, context=context)
    
    def _get_line_order_ids(self, cr, uid, ids, context=None):
        """
        return the list of lunch.order.lines ids to which belong the  lunch.order 'ids'
        """
        result = set()
        for lunch_order in self.browse(cr, uid, ids, context=context):
            for lines in lunch_order.order_line_ids:
                result.add(lines.id)
        return list(result)

    _columns = {
        'name': fields.related('product_id', 'name', readonly=True),
        'order_id': fields.many2one('lunch.order', 'Order', ondelete='cascade'),
        'product_id': fields.many2one('lunch.product', 'Product', required=True),
        'date': fields.related('order_id', 'date', type='date', string="Date", readonly=True, store={
            'lunch.order': (_get_line_order_ids, ['date'], 10), 
            'lunch.order.line': (lambda self, cr, uid, ids, ctx: ids, [], 10),
            }),
        'supplier': fields.related('product_id', 'supplier', type='many2one', relation='res.partner', string="Supplier", readonly=True, store=True),
        'user_id': fields.related('order_id', 'user_id', type='many2one', relation='res.users', string='User', readonly=True, store=True),
        'note': fields.text('Note'),
        'price': fields.float("Price"),
        'state': fields.selection([('new', 'New'), \
                                    ('confirmed', 'Received'), \
                                    ('ordered', 'Ordered'),  \
                                    ('cancelled', 'Cancelled')], \
                                'Status', readonly=True, select=True),
        'cashmove': fields.one2many('lunch.cashmove', 'order_id', 'Cash Move', ondelete='cascade'),

    }
    _defaults = {
        'state': 'new',
    }


class lunch_product(osv.Model):
    """ 
    lunch product 
    """
    _name = 'lunch.product'
    _description = 'lunch product'
    _columns = {
        'name': fields.char('Product', required=True),
        'category_id': fields.many2one('lunch.product.category', 'Category', required=True),
        'description': fields.text('Description', size=256),
        'price': fields.float('Price', digits=(16,2)), #TODO: use decimal precision of 'Account', move it from product to decimal_precision
        'supplier': fields.many2one('res.partner', 'Supplier'),
    }

class lunch_product_category(osv.Model):
    """ 
    lunch product category 
    """
    _name = 'lunch.product.category'
    _description = 'lunch product category'
    _columns = {
        'name': fields.char('Category', required=True), #such as PIZZA, SANDWICH, PASTA, CHINESE, BURGER, ...
    }

class lunch_cashmove(osv.Model):
    """ 
    lunch cashmove => order or payment 
    """
    _name = 'lunch.cashmove'
    _description = 'lunch cashmove'
    _columns = {
        'user_id': fields.many2one('res.users', 'User Name', required=True),
        'date': fields.date('Date', required=True),
        'amount': fields.float('Amount', required=True), #depending on the kind of cashmove, the amount will be positive or negative
        'description': fields.text('Description'), #the description can be an order or a payment
        'order_id': fields.many2one('lunch.order.line', 'Order', ondelete='cascade'),
        'state': fields.selection([('order','Order'), ('payment','Payment')], 'Is an order or a Payment'),
    }
    _defaults = {
        'user_id': lambda self, cr, uid, context: uid,
        'date': fields.date.context_today,
        'state': 'payment',
    }

class lunch_alert(osv.Model):
    """ 
    lunch alert 
    """
    _name = 'lunch.alert'
    _description = 'Lunch Alert'
    _columns = {
        'message': fields.text('Message', size=256, required=True),
        'alter_type': fields.selection([('specific', 'Specific Day'), \
                                    ('week', 'Every Week'), \
                                    ('days', 'Every Day')], \
                                string='Recurrency', required=True, select=True),
        'specific_day': fields.date('Day'),
        'monday': fields.boolean('Monday'),
        'tuesday': fields.boolean('Tuesday'),
        'wednesday': fields.boolean('Wednesday'),
        'thursday': fields.boolean('Thursday'),
        'friday': fields.boolean('Friday'),
        'saturday': fields.boolean('Saturday'),
        'sunday':  fields.boolean('Sunday'),
        'active_from': fields.float('Between', required=True),
        'active_to': fields.float('And', required=True),
    }
    _defaults = {
        'alter_type': 'specific',
        'specific_day': fields.date.context_today,
        'active_from': 7,
        'active_to': 23,
    }
