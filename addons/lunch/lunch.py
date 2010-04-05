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

from osv import osv, fields
import time

class lunch_category(osv.osv):
    """ Lunch category """

    _name = 'lunch.category'
    _description = "Category"

    _columns = {
        'name': fields.char('Name', required=True, size=50),
    }
    _order = 'name'

lunch_category()


class lunch_product(osv.osv):
    """ Lunch Product """

    _name = 'lunch.product'
    _description = "Lunch Product"

    def _category_name_get(self, cr, uid, context={}):

        """ Get category name
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param context: A standard dictionary for contextual values"""

        obj = self.pool.get('lunch.category')
        cat_ids = obj.search(cr, uid, [])
        res = obj.read(cr, uid, cat_ids, ['name', 'category'])
        return [(str(r['id']), r['name']) for r in res]+ [('0','')]

    _columns = {
        'name': fields.char('Name', size=50, required=True),
        'category_id': fields.selection(_category_name_get, 'Category', size=32),
        'description': fields.char('Description', size=128, required=False),
        'price': fields.float('Price', digits=(16,2)),
        'active': fields.boolean('Active'),
    }

    _defaults = {
        'active': lambda *a : True,
        }

lunch_product()


class lunch_cashbox(osv.osv):
    """ cashbox for Lunch """

    _name = 'lunch.cashbox'
    _description = "Cashbox for Lunch "


    def amount_available(self, cr, uid, ids, field_name, arg, context):

        """ count available amount
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of create menu’s IDs
        @param context: A standard dictionary for contextual values """

        cr.execute("SELECT box,sum(amount) from lunch_cashmove where active = 't' group by box")
        amount = dict(cr.fetchall())
        for i in ids:
            amount.setdefault(i, 0)
        return amount

    _columns = {
        'manager': fields.many2one('res.users', 'Manager'),
        'name': fields.char('Name', size=30, required=True, unique = True),
        'sum_remain': fields.function(amount_available, method=True, string='Remained Total'),
        }

lunch_cashbox()


class lunch_cashmove(osv.osv):
    """ Move cash """

    _name = 'lunch.cashmove'
    _description = "Move cash"

    _columns = {
        'name': fields.char('Name', size=128),
        'user_cashmove': fields.many2one('res.users', 'User Name', required=True),
        'amount': fields.float('Amount', digits=(16, 2)),
        'box': fields.many2one('lunch.cashbox', 'Box Name', size=30, required=True),
        'active': fields.boolean('Active'),
        'create_date': fields.datetime('Created date', readonly=True),
        }

    _defaults = {
    'active': lambda *a: True,
    }

lunch_cashmove()


class lunch_order(osv.osv):
    """ Apply lunch order """

    _name = 'lunch.order'
    _description = "Lunch Order"
    _rec_name = "user_id"

    def _price_get(self, cr, uid, ids, name, args, context=None):

        """ Get Price of Product
         @param cr: the current row, from the database cursor,
         @param uid: the current user’s ID for security checks,
         @param ids: List of Lunch order’s IDs
         @param context: A standard dictionary for contextual values """

        res = {}
        for price in self.browse(cr, uid, ids):
            res[price.id] = price.product.price
        return res

    _columns = {
        'user_id': fields.many2one('res.users', 'User Name', required=True, \
            readonly=True, states={'draft':[('readonly', False)]}),
        'product': fields.many2one('lunch.product', 'Product', required=True, \
            readonly=True, states={'draft':[('readonly', False)]}, change_default=True),
        'date': fields.date('Date', readonly=True, states={'draft':[('readonly', False)]}),
        'cashmove': fields.many2one('lunch.cashmove', 'CashMove' , readonly=True),
        'descript': fields.char('Description Order', readonly=True, size=50, \
            states = {'draft':[('readonly', False)]}),
        'state': fields.selection([('draft', 'Draft'), ('confirmed', 'Confirmed'), ], \
            'State', readonly=True, select=True),
        'price': fields.function(_price_get, method=True, string="Price"),
    }

    _defaults = {
        'user_id': lambda self,cr,uid,context: uid,
        'date': lambda self,cr,uid,context: time.strftime('%Y-%m-%d'),
        'state': lambda self,cr,uid,context: 'draft',
    }

    def confirm(self, cr, uid, ids, box, context):

        """ confirm order
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of confirm order’s IDs
        @param context: A standard dictionary for contextual values """

        cashmove_ref = self.pool.get('lunch.cashmove')
        for order in self.browse(cr, uid, ids):
            if order.state == 'confirmed':
                continue
            new_id = cashmove_ref.create(cr, uid, {'name': order.product.name+' order',
                            'amount':-order.product.price,
                            'user_cashmove':order.user_id.id,
                            'box':box,
                            'active':True,
                            })
            self.write(cr, uid, [order.id], {'cashmove': new_id, 'state': 'confirmed'})
        return {}

    def lunch_order_cancel(self, cr, uid, ids, context):

        """" cancel order
         @param cr: the current row, from the database cursor,
         @param uid: the current user’s ID for security checks,
         @param ids: List of create menu’s IDs
         @param context: A standard dictionary for contextual values """

        orders = self.browse(cr, uid, ids)
        for order in orders:
            if not order.cashmove:
                continue
        if order.cashmove.id:
            self.pool.get('lunch.cashmove').unlink(cr, uid, [order.cashmove.id])
        self.write(cr, uid, ids, {'state':'draft'})
        return {}

    def onchange_product(self, cr, uid, ids, product):

        """ Get price for Product
         @param cr: the current row, from the database cursor,
         @param uid: the current user’s ID for security checks,
         @param ids: List of create menu’s IDs
         @product: Product To Ordered """

        if not product:
            return {'value': {'price': 0.0}}
        price = self.pool.get('lunch.product').read(cr, uid, product, ['price'])['price']
        return {'value': {'price': price}}

lunch_order()


class report_lunch_amount(osv.osv):
    """ Lunch Amount Report """

    _name = 'report.lunch.amount'
    _description = "Amount available by user and box"
    _auto = False
    _rec_name = "user"

    _columns = {
        'user_id': fields.many2one('res.users', 'User Name', readonly=True),
        'amount': fields.float('Amount', readonly=True, digits=(16, 2)),
        'box': fields.many2one('lunch.cashbox', 'Box Name', size=30, readonly=True),
        }

    def init(self, cr):

        """ @param cr: the current row, from the database cursor"""

        cr.execute("""
            create or replace view report_lunch_amount as (
                select
                    min(lc.id) as id,
                    lc.user_cashmove as user_id,
                    sum(amount) as amount,
                    lc.box as box
                from
                    lunch_cashmove lc
                where
                    active = 't'
                group by lc.user_cashmove, lc.box
                )""")

report_lunch_amount()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

