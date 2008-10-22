# -*- encoding: utf-8 -*-
import time

from osv import osv, fields
import pooler

#
# Type of type of products (food, drink, lsd, other...)
#
class sandwich_product_type(osv.osv):
    _name = 'sandwich.product.type'
    _columns = {
        'name': fields.char('Name of the type', size=20, required=True),
        'description': fields.char('Type\'s description', size=255),
    }
sandwich_product_type()


#
# Type Of Sandwich
#
class sandwich_product(osv.osv):
    _name = 'sandwich.product'
    _columns = {
        'name': fields.char('Product name', size=50, required=True),
        'price': fields.float('Product price'),
        'product_type_id': fields.many2one('sandwich.product.type','Type of product'),
    }
sandwich_product()


#
# Sandwich command
#
class sandwich_order(osv.osv):
    _name = 'sandwich.order'
    _columns = {
        'name': fields.char('Name', size=50, required=True),
        'date': fields.date('Order date'),
        'order_lines': fields.one2many('sandwich.order.line','order_id','Order lines'),
        'note': fields.text('Notes'),
        'partner': fields.many2one('res.partner','Partner', required=True),
    }
    _defaults = {
        'date': lambda *a: time.strftime('%Y-%m-%d'),
    }
sandwich_order()


#
# Sandwich lines of command
#
class sandwich_order_line(osv.osv):
    _name = 'sandwich.order.line'
    _columns = {
        'name': fields.char('Description', size=50, required=True),
        'product_id': fields.many2one('sandwich.product', 'Product'),
        'user_id': fields.many2one('res.users', 'User id', required=True),
        'quantity': fields.integer('Quantity', required=True),
        'order_id': fields.many2one('sandwich.order', 'Order'),
        'date': fields.date('Date'),
        'product_type_id':fields.many2one('sandwich.product.type','Product type',change_default=True),
    }
    _defaults = {
        'date': lambda *a: time.strftime('%Y-%m-%d'),
        'user_id': lambda self, cr, uid, c: uid,
        'quantity': lambda *a: 1
    }

    def onchange_user_id(self, cr, uid, id, user_id, product_type_id, context={}, *args):
        # print id, user_id, product_type_id, context
        if (not user_id) or (not product_type_id):
            return {}
        cr.execute('SELECT product_id,name,quantity FROM sandwich_order_line WHERE user_id=%d AND product_type_id=%d ORDER BY date DESC LIMIT 1', (user_id, product_type_id))
        res = cr.dictfetchone()
        if res:
            return {'value': res}
        # else
        return {'value': {'product_id': False, 'name': '', 'quantity': 1}}
    
    def onchange_product_type_id(self, cr, uid, id, user_id, product_type_id, context={}):
        if (not product_type_id) or (not user_id):
            return {}
        cr.execute('SELECT product_id,name,quantity FROM sandwich_order_line WHERE user_id=%d AND product_type_id=%d ORDER BY date DESC LIMIT 1', (user_id, product_type_id))
        res = cr.dictfetchone()
        if res:
            return {'value': res}
        # else
        return {'value': {'product_id': False, 'name': '', 'quantity': 1}}

    def onchange_product_id(self, cr, uid, id, product_id, context={}):
        if not product_id:
            return {}
        res = pooler.get_pool(cr.dbname).get('sandwich.product').read(cr, uid, [ product_id ], ['name','product_type_id'])
        return {'value': res}
        #return {'value': {'name': name or product_id.name, 'product_type_id': product_id.product_type_id}}

sandwich_order_line()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

