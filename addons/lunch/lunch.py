# -*- encoding: utf-8 -*-
from osv import osv, fields
import time

class lunch_category(osv.osv):
    _name = 'lunch.category'
    _description = "Category"

    _columns = {
        'name': fields.char('Name', required=True, size=50),
    }

    _order = 'name'

lunch_category()

class lunch_product(osv.osv):
    _name = 'lunch.product'

    def _category_name_get(self, cr, uid, context={}):
        obj = self.pool.get('lunch.category')
        cat_ids= obj.search(cr,uid,[])
        res = obj.read(cr,uid,cat_ids,['name', 'category'])
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
    _name='lunch.cashbox'

    def amount_available(self, cr, uid, ids, field_name, arg, context):
        cr.execute("SELECT box,sum(amount) from lunch_cashmove where active = 't' group by box")
        r = dict(cr.fetchall())
        for i in ids :
            r.setdefault(i,0)
        return r

    _columns={
        'manager':fields.many2one('res.users','Manager'),
        'name':fields.char('Name',size=30,required=True, unique = True),
        'sum_remain': fields.function(amount_available, method=True, string='Remained Total'),
        }

lunch_cashbox()




class lunch_cashmove(osv.osv):
    _name= 'lunch.cashmove'

    _columns={
        'name': fields.char('Name',size=128),
        'user_cashmove': fields.many2one('res.users','User Name', required=True),
        'amount': fields.float('Amount', digits=(16,2)),
        'box':fields.many2one('lunch.cashbox','Box Name',size=30,required=True),
        'active':fields.boolean('Active'),
        'create_date': fields.datetime('Created date', readonly=True),
        }

    _defaults={
    'active': lambda *a: True,
    }

lunch_cashmove()



class lunch_order(osv.osv):
    _name='lunch.order'
    _rec_name= "user_id"

    def _price_get(self, cr, uid, ids, name, args, context=None):
        res = {}
        for o in self.browse(cr, uid, ids):
            res[o.id] = o.product.price
        return res

    _columns={
        'user_id': fields.many2one('res.users','User Name', required=True,
            readonly=True, states={'draft':[('readonly',False)]}),
        'product':fields.many2one('lunch.product','Product', required=True,
            readonly=True, states={'draft':[('readonly',False)]}, change_default=True),
        'date': fields.date('Date',readonly=True,states={'draft':[('readonly',False)]}),
        'cashmove':fields.many2one('lunch.cashmove', 'CashMove' , readonly=True  ),
        'descript':fields.char('Description Order', readonly=True, size=50,
            states={'draft':[('readonly',False)]}),
        'state': fields.selection([('draft','Draft'), ('confirmed','Confirmed'),],
            'State', readonly=True, select=True),
        'price': fields.function(_price_get, method=True, string="Price"),
    }

    _defaults={
        'user_id': lambda self,cr,uid,context: uid,
        'date': lambda self,cr,uid,context: time.strftime('%Y-%m-%d'),
        'state': lambda self,cr,uid,context: 'draft',
    }

    def confirm(self,cr,uid,ids,box,context):
        cashmove_ref= self.pool.get('lunch.cashmove')
        for order in self.browse(cr,uid,ids):
            if order.state == 'confirmed':
                continue
            new_id= cashmove_ref.create(cr,uid,{'name': order.product.name+' order',
                            'amount':-order.product.price,
                            'user_cashmove':order.user_id.id,
                            'box':box,
                            'active':True,
                            })
            self.write(cr,uid,[order.id],{'cashmove':new_id, 'state':'confirmed'})
        return {}

    def lunch_order_cancel(self,cr,uid,ids,context):
        orders= self.browse(cr,uid,ids)
        for order in orders:
            if not order.cashmove:
                continue
            self.pool.get('lunch.cashmove').unlink(cr, uid, [order.cashmove.id])
        self.write(cr,uid,ids,{'state':'draft'})
        return {}

    def onchange_product(self, cr, uid, ids, product):
        if not product:
            return {'value': {'price': 0.0}}
        price = self.pool.get('lunch.product').read(cr, uid, product, ['price'])['price']
        return {'value': {'price': price}}

lunch_order()

class report_lunch_amount(osv.osv):
    _name='report.lunch.amount'
    _description = "Amount available by user and box"
    _auto = False
    _rec_name= "user"

    _columns = {
        'user_id': fields.many2one('res.users','User Name',readonly=True),
        'amount': fields.float('Amount', readonly=True, digits=(16,2)),
        'box':fields.many2one('lunch.cashbox','Box Name',size=30,readonly=True),
        }

    def init(self, cr):
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

