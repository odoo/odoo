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

from osv import osv
from osv import fields
from tools.translate import _
import decimal_precision as dp
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

class product_price_unit(osv.osv):
    _name = "product.price.unit"
    _description = 'Product Price Unit'
    _order = "coefficient asc,name"
    _columns = {
       'code': fields.char('PU', size=3, required=True, translate=True, help="A three characters code to be placed next to the price"),
       'coefficient': fields.integer('Coefficient', required=True, help="Values will be calculated as price / coefficient"),
       'name': fields.char('Price per Unit', size=32, required=True, translate=True, help="Enter something like: Price for 100 units"),
    }

product_price_unit()

class product_category(osv.osv):
    _inherit = "product.category"
    _name = "product.category"

    _columns = {
        'property_stock_location': fields.property('stock.location',
            relation='stock.location', type='many2one',
            string='Stock Location', method=True, view_load=True,
            help="This location will be proposed for the stock move"),
        'allow_negative_stock' : fields.boolean('Allow Negative Stock', help="Allows negative stock quantities for this category - use with care !"),
    }
product_category()

class product_template(osv.osv):
    _inherit = "product.template"
    _name = "product.template"

    def _get_price_unit_id(self, cr, uid, *args):
        cr.execute('select id from product_price_unit where coefficient = 1')
        res = cr.fetchone()
        return res and res[0] or False
    
    _columns = {
        'price_unit_id': fields.many2one('product.price.unit','Price Unit', help="Use if Price is not defined for UoM"),
        'standard_price_coeff': fields.float(string='Standard Price/Coeff',digits=(16,8)) ,
        'list_price_coeff': fields.float(string='List Price/Coeff',digits=(16,8)),
        'property_stock_location': fields.property('stock.location',
            relation='stock.location', type='many2one',
            string='Stock Location', method=True, view_load=True,
            help="This location will be proposed for the stock move"),
        'allow_negative_stock' : fields.boolean('Allow Negative Stock', help="Allows negative stock quantities - use with care !"),

    }
    
    _defaults = {
        'price_unit_id': _get_price_unit_id,
    }
    
    def init(self, cr):
        cr.execute("""
            update product_template
               set price_unit_id = (select id from product_price_unit where coefficient = 1)
             where price_unit_id is null
               and exists (select id from product_price_unit where coefficient = 1)"""
            )

product_template()

class product_product(osv.osv):
    _name = "product.product"
    _inherit = "product.product"

    def _avg_price(self, cr, uid, ids, field_names=None, arg=False, context={}):
        res = {} 
        for product in self.browse(cr, uid, ids, context=context):
            avg_price = 0.0
            value = self._stock_value( cr, uid, [product.id], ['stock_value',], arg, context)[product.id]['stock_value']
            qty = self._product_available( cr, uid, ids, ['qty_available',], arg, context)[product.id]['qty_available']
            if qty > 0.0 and value > 0.0:
               pu = self.pool.get('product.price.unit').browse(cr, uid, product.price_unit_id.id)
               coeff = pu.coefficient
               avg_price = value / qty * coeff
            res[product.id] = avg_price  
        return res
    
    def get_stock_value(self, cr, uid, ids, context=None):
            if not context:
                context = {}
            states=context.get('states',[])
            what=context.get('what',())
            if not ids:
                ids = self.search(cr, uid, [])
            res = {}.fromkeys(ids, 0.0)
            if not ids:
                return res

            if context.get('shop', False):
                cr.execute('select warehouse_id from sale_shop where id=%s', (int(context['shop']),))
                res2 = cr.fetchone()
                if res2:
                    context['warehouse'] = res2[0]

            if context.get('warehouse', False):
                cr.execute('select lot_stock_id from stock_warehouse where id=%s', (int(context['warehouse']),))
                res2 = cr.fetchone()
                if res2:
                    context['location'] = res2[0]

            if context.get('location', False):
                if type(context['location']) == type(1):
                    location_ids = [context['location']]
                else:
                    location_ids = context['location']
            else:
                cr.execute("select lot_stock_id from stock_warehouse")
                location_ids = [id for (id,) in cr.fetchall()]

            # build the list of ids of children of the location given by id
            if context.get('compute_child',True):
                child_location_ids = self.pool.get('stock.location').search(cr, uid, [('location_id', 'child_of', location_ids)])
                location_ids= len(child_location_ids) and child_location_ids or location_ids
            else:
                location_ids= location_ids

            states_str = ','.join(map(lambda s: "'%s'" % s, states))

            uoms_o = {}
            product2uom = {}
            for product in self.browse(cr, uid, ids, context=context):
                product2uom[product.id] = product.uom_id.id
                uoms_o[product.uom_id.id] = product.uom_id

            prod_ids_str = ','.join(map(str, ids))
            location_ids_str = ','.join(map(str, location_ids))
            results = []
            results2 = []

            from_date=context.get('from_date',False)
            to_date=context.get('to_date',False)
            date_str=False
            if from_date and to_date:
                date_str="date_planned>='%s' and date_planned<='%s'"%(from_date,to_date)
            elif from_date:
                date_str="date_planned>='%s'"%(from_date)
            elif to_date:
                date_str="date_planned<='%s'"%(to_date)

            cr.execute(
                    'select sum('\
                    'case when location_dest_id in ('+location_ids_str+') then  move_value else 0 end + '\
                    'case when location_id      in ('+location_ids_str+') then -move_value else 0 end '\
                    '), product_id '\
                    'from stock_move '\
                    'where (location_id  in ('+location_ids_str+') '\
                    'or location_dest_id in ('+location_ids_str+')) '\
                    'and product_id in ('+prod_ids_str+') '\
                    'and state in ('+states_str+') '+ (date_str and 'and '+date_str+' ' or '') +''\
                    'group by product_id'
                )
            results = cr.fetchall()

            for amount, prod_id in results:
                if amount: res[prod_id] += amount
            return res
    
    def _stock_value(self, cr, uid, ids, field_names=None, arg=False, context={}):
        if not field_names:
            field_names=[]
        res = {}
        for id in ids:
            res[id] = {}.fromkeys(field_names, 0.0)
        for f in field_names:
            c = context.copy()
            if f=='stock_value':
                c.update({ 'states':('done',), 'what':('in', 'out') })
            stock=self.get_stock_value(cr,uid,ids,context=c)
            for id in ids:
                res[id][f] = stock.get(id, 0.0)
        return res
    
    def _product_available(self, cr, uid, ids, field_names=None, arg=False, context={}):
        res = super(product_product, self)._product_available(cr, uid, ids, field_names, arg, context)
        for f in field_names:
            c = context.copy()
            if f=='stock_value':
                c.update({ 'states':('done',), 'what':('in', 'out') })
            stock = self.get_product_available(cr, uid, ids, context=c)
            for id in ids:
                res[id][f] = stock.get(id, 0.0)
        return res
    
    _columns = {
        'stock_value': fields.function(_stock_value, method=True, type='float', string='Value', help="Current Value products in selected locations or all internal if none have been selected.", multi='stock_value'),
        'average_price': fields.function(_avg_price, method=True, type='float', string='Average Price',digits=(16,4)),
    }

    def _check_allow_negative_stock(self, cr, uid, ids):
        for product in self.browse(cr, uid, ids):
            if product.qty_available < 0.0:
               allow_negative = product.allow_negative_stock
               if not allow_negative:
                  allow_neagtive = product.categ_id.allow_negative_stock
               if allow_negative != True :
                   return False
        return True

    _constraints = [(_check_allow_negative_stock, 'Error: Negative stock quantities are not allowed for this product or product category', ['name']),]

    
    def on_change_price_unit(self, cr, uid, ids,price_unit_id,standard_price,list_price):
         standard_price_coeff = ''
         list_price_coeff=''
         if price_unit_id:
             pu = self.pool.get('product.price.unit').browse(cr, uid, [price_unit_id])[0]
             coeff =  pu.coefficient
             standard_price_coeff = standard_price / coeff
             list_price_coeff     = list_price     / coeff
             return {'value':{'standard_price_coeff': standard_price_coeff, 'list_price_coeff': list_price_coeff }}

    def name_get(self, cr, uid, ids, context={}):
        results = super(product_product, self).name_get(cr, uid, ids, context)
        new_results = []
        for product_id, product_name in results:           
            product = self.browse(cr, uid, product_id, context)
            if product.price_unit_id and product.price_unit_id.name:
                product_name = "%s (%s)" %(product_name, product.price_unit_id.name)
            new_results.append((product_id, product_name))
        return new_results
    
    #
    # returns the price respecting the price unit for multiplications qty * price / coeff
    # 
    def price_coeff_get(self, cr, uid, ids, ptype='list_price', context={}):
        res = {}
        for product in self.browse(cr, uid, ids, context=context):
            coeff = 1.0
            if product.price_unit_id:
                coeff = product.price_unit_id.coefficient
            res[product.id] = product.price_get(ptype, context)[product.id] / coeff 
            
        return res   

product_product()

class account_invoice_line(osv.osv):
    _name = "account.invoice.line"
    _inherit = "account.invoice.line"

    def _get_price_unit_id(self, cr, uid, *args):
        cr.execute('select id from product_price_unit where coefficient = 1')
        res = cr.fetchone()
        return res and res[0] or False

    def _amount_line(self, cr, uid, ids, prop, unknow_none,unknow_dict):
        res = {}
        cur_obj=self.pool.get('res.currency')
        for line in self.browse(cr, uid, ids):
            if line.price_unit_id:
                if line.invoice_id:
                    res[line.id] = line.price_unit * line.quantity * (1-(line.discount or 0.0)/100.0) / line.price_unit_id.coefficient
                    cur = line.invoice_id.currency_id
                    res[line.id] = cur_obj.round(cr, uid, cur, res[line.id])
                else:
                    res[line.id] = round(line.price_unit * line.quantity * (1-(line.discount or 0.0)/100.0)/ line.price_unit_id.coefficient,self.pool.get('decimal.precision').precision_get(cr, uid, 'Account'))
        return res

    _columns = {
        'price_unit_id': fields.many2one('product.price.unit','Price Unit', help="Use if Price is not defined for UoM"),
        'price_subtotal': fields.function(_amount_line, method=True, string='Subtotal',store=True, type="float", digits_compute= dp.get_precision('Account')),
    }
    _defaults = {
        'price_unit_id': _get_price_unit_id,
    }

    def price_product_id_change(self, cr, uid, ids, product, uom, qty=0, name='', type='out_invoice', partner_id=False, fposition_id=False, price_unit=False, price_unit_id=False, address_invoice_id=False, currency_id=False, context=None):
        result = super(account_invoice_line, self).product_id_change(cr, uid, ids, product, uom, qty, name, type, partner_id, fposition_id, price_unit, address_invoice_id, currency_id, context)
        if product and 'value' in result:
            pu = self.pool.get('product.product').browse(cr, uid, product)
            if pu.price_unit_id:
                result['value']['price_unit_id'] = pu.price_unit_id.id
        return result

account_invoice_line()

class account_analytic_line(osv.osv):
    _inherit = 'account.analytic.line'
    
    def on_change_unit_amount(self, cr, uid, id, prod_id, unit_amount,company_id,
            unit=False, context=None):
        res = super(account_analytic_line, self).on_change_unit_amount(cr, uid, id, prod_id, unit_amount, company_id, unit, context)
        product_obj = self.pool.get('product.product')
        if prod_id:
            prod = product_obj.browse(cr, uid, prod_id)
            amount_unit = prod.price_coeff_get()[prod.id]
            amount = amount_unit * unit_amount or 1.0
            res['value']['amount'] = - round(amount, 2)
        return res
    
account_analytic_line()

class account_invoice_tax(osv.osv):
    _inherit = "account.invoice.tax"
    
    def compute(self, cr, uid, invoice_id, context={}):
        tax_grouped = super(account_invoice_tax, self).compute(cr, uid, invoice_id, context)
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        inv = self.pool.get('account.invoice').browse(cr, uid, invoice_id, context)
        company_currency = inv.company_id.currency_id.id
        for t in tax_grouped.values():
            t['base'] = 0.0
            t['base_amount'] = 0.0
        for line in inv.invoice_line:
            for tax in tax_obj.compute(cr, uid, line.invoice_line_tax_id, (line.price_unit* (1-(line.discount or 0.0)/100.0/line.price_unit_id.coefficient)), line.quantity, inv.address_invoice_id.id, line.product_id, inv.partner_id):
                for t in tax_grouped.values():
                    t['base'] += tax['price_unit'] * line['quantity'] / line['price_unit_id'].coefficient
                    if inv.type in ('out_invoice','in_invoice'):
                        t['base_amount'] = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, t['base'] * tax['base_sign'], context={'date': inv.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
                    else:
                        t['base_amount'] = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, t['base'] * tax['ref_base_sign'], context={'date': inv.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
        return tax_grouped
    
account_invoice_tax()

class hr_expense_line(osv.osv):
    _name = "hr.expense.line"
    _inherit = "hr.expense.line"

    def _get_price_unit_id(self, cr, uid, *args):
        cr.execute('select id from product_price_unit where coefficient = 1')
        res = cr.fetchone()
        return res and res[0] or False

    def _amount(self, cr, uid, ids, field_name, arg, context):
        if not len(ids):
            return {}
        cr.execute("SELECT l.id,COALESCE(SUM(l.unit_amount*l.unit_quantity/pu.coefficient),0) AS amount FROM hr_expense_line l ,product_price_unit pu WHERE pu.id = l.price_unit_id and l.id =ANY(%s) GROUP BY l.id ",(ids,))
        res = dict(cr.fetchall())
        return res

    _columns = {
        'price_unit_id': fields.many2one('product.price.unit','Price Unit', help="Use if Price is not defined for UoM"),
        'total_amount': fields.function(_amount, method=True, string='Total'),
    }    
    _defaults = {
        'price_unit_id': _get_price_unit_id,
    }
hr_expense_line()

class hr_expense_expense(osv.osv):
    _name = "hr.expense.expense"
    _inherit = "hr.expense.expense"

    def _amount(self, cr, uid, ids, field_name, arg, context):
        if not len(ids):
            return {}
        cr.execute("SELECT s.id,COALESCE(SUM(l.unit_amount*l.unit_quantity/pu.coefficient),0) AS amount FROM hr_expense_expense s LEFT OUTER JOIN hr_expense_line l ON (s.id=l.expense_id) LEFT JOIN product_price_unit pu ON (pu.id=l.price_unit_id) WHERE s.id = ANY(%s) GROUP BY s.id ",(ids,))
        res = dict(cr.fetchall())
        return res

    _columns = {
        'amount': fields.function(_amount, method=True, string='Total Amount'),
    }

hr_expense_expense()

class mrp_bom(osv.osv):
    _inherit = 'mrp.bom'
    
    def _get_price_unit_id(self, cr, uid, *args):
        cr.execute('select id from product_price_unit where coefficient = 1')
        res = cr.fetchone()
        return res and res[0] or False
    
    _columns = {
        'price_unit_id': fields.many2one('product.price.unit','Price Unit' ),
    }
    
    _defaults = {
        'price_unit_id': _get_price_unit_id,
    }
mrp_bom()

class stock_move(osv.osv):
    _inherit = 'stock.move'
    _columns = {
        'price_unit_id': fields.many2one('product.price.unit','Price Unit internal'),
        'price_unit_sale_id': fields.many2one('product.price.unit','Price Unit Sale' ),
        'move_value': fields.float('Amount', digits_compute= dp.get_precision('Account')),
        'move_value_sale': fields.float('Amount Sale',digits_compute= dp.get_precision('Account') ),
    }
stock_move()

class stock_avg_price(osv.osv):
    _name = "stock_avg_price"
    def init(self, cr):
        cr.execute("SELECT true FROM pg_catalog.pg_language WHERE lanname = 'plpgsql';")
        if not cr.fetchall():
            cr.execute("create language plpgsql;")

        cr.execute("""
CREATE OR REPLACE FUNCTION get_stock_avg_price(product_id_i integer,location_id_i  integer) RETURNS numeric AS $$
DECLARE 
 avg_price decimal(16,8);                    
 value     float;                    
 qty       float;                    
 usage_p   varchar(32);

BEGIN

select into usage_p usage
  from stock_location
 where id = location_id_i;

if usage_p = 'internal'
then 
select into value,qty
       sum(case when location_id = location_id_i then -move_value
                when location_dest_id = location_id_i then move_value 
                else 0 end),
       sum(case when location_id = location_id_i then -product_qty
                when location_dest_id = location_id_i then product_qty 
                else 0 end)
  from stock_move
 where product_id = product_id_i
   and (location_id = location_id_i or location_dest_id = location_id_i)
   and state = 'done'; 

if qty = 0
 then avg_price = 0;
 else avg_price = value/qty;
end if;
end if;

if avg_price is null
 then avg_price = 0;
end if;
         
                       
RETURN avg_price;
END;
$$ LANGUAGE plpgsql;""")
stock_avg_price()

class sale_order(osv.osv):
    _inherit = 'sale.order'
    
    def _amount_line_tax(self, cr, uid, line, context={}):
        val = 0.0
        for c in self.pool.get('account.tax').compute(cr, uid, line.tax_id, line.price_unit * (1-(line.discount or 0.0)/100.0)/ line.price_unit_id.coefficient, line.product_uom_qty, line.order_id.partner_invoice_id.id, line.product_id, line.order_id.partner_id):
            val+= c['amount']
        return val
    
    def action_ship_create(self, cr, uid, ids, *args):
        val = super(sale_order, self).action_ship_create(cr, uid, ids, *args)
        move_obj = self.pool.get('stock.move')
        for order in self.browse(cr, uid, ids, context={}):
            for line in order.order_line:
                now = datetime.now()
                order_date = datetime.strptime(order.date_order,"%Y-%m-%d")
                date_planned = order_date + relativedelta(days=line.delay or 0.0)
                if date_planned < now:
                   date_planned = now

                users_roles = self.pool.get('res.users').browse(cr, uid, uid).roles_id
                for role in users_roles:
                   if role.name=='Document date manual data':
                       date_planned = order_date
                if line.product_id and line.product_id.product_tmpl_id.type in ('product', 'consu'):
                    location_id = line.product_id.property_stock_location.id
                    if not location_id:
                        location_id = line.product_id.categ_id.property_stock_location.id
                    if not location_id:
                        location_id = order.shop_id.warehouse_id.lot_stock_id.id
                    move_ids = move_obj.search(cr, uid, [('sale_line_id','=',line.id)])
                    cr.execute("""select get_stock_avg_price(%s,%s) ; """ % (line.product_id.id,location_id))
                    res = cr.fetchone()
                    stock_avg_price = (res and res[0]) or False
                    move_obj.write(cr, uid, move_ids, {
                                                       'date': line.order_id.date_order,
                                                       'price_unit' : stock_avg_price,
                                                       'price_unit_id': line.product_id.price_unit_id.id,
                                                       'price_unit_sale_id': line.price_unit_id.id,
                                                       'move_value' : line.product_uom_qty * stock_avg_price,
                                                       'move_value_sale': line.price_subtotal,
                                                       })
        return True
sale_order()

class sale_order_line(osv.osv):
    _inherit = 'sale.order.line'
    
    def _get_price_unit_id(self, cr, uid, *args):
        cr.execute('select id from product_price_unit where coefficient = 1')
        res = cr.fetchone()
        return res and res[0] or False
    
    def _amount_line(self, cr, uid, ids, field_name, arg, context):
        res = {}
        cur_obj = self.pool.get('res.currency')
        for line in self.browse(cr, uid, ids):
            res[line.id] = line.price_unit * line.product_uom_qty * (1 - (line.discount or 0.0) / 100.0) / line.price_unit_id.coefficient
            cur = line.order_id.pricelist_id.currency_id
            res[line.id] = cur_obj.round(cr, uid, cur, res[line.id])
        return res
    
    _columns = {
        'price_unit_id': fields.many2one('product.price.unit','Price Unit', required=True),
    }
    
    _defaults = {
        'price_unit_id': _get_price_unit_id,
    }
    
    def invoice_line_create(self, cr, uid, ids, context={}):
        created_ids = super(sale_order_line,self).invoice_line_create(cr, uid, ids, context=context)
        inv_line_obj = self.pool.get('account.invoice.line')
        def _get_line_pu_id(line):
            return line.price_unit_id.id
        for line in self.browse(cr, uid, ids, context):
            pu_id = _get_line_pu_id(line)
            inv_line_obj.write(cr, uid, created_ids, {'price_unit_id': pu_id})
        return created_ids
    
    def product_id_change(self, cr, uid, ids, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False, 
            fiscal_position=False, flag=False):
        result = super(sale_order_line, self).product_id_change(cr, uid, ids, pricelist, 
            product, qty, uom, qty_uos, uos, name, partner_id, lang, 
            update_tax, date_order, packaging, fiscal_position, flag)
        if not product:
            return result

        product_obj = self.pool.get('product.product')
        product_obj = product_obj.browse(cr, uid, product)
        pu_id = product_obj.price_unit_id.id
        result['value']['price_unit_id'] = pu_id

        pname =  product_obj.name
        if product_obj.variants: 
            pname = pname + ' ['+product_obj.variants + ']'
        if product_obj.price_unit_id and product_obj.price_unit_id.coefficient != 1.0:
            pname = pname + ' (' + product_obj.price_unit_id.name + ')'
        result['name'] = pname
        return result
    
sale_order_line()

class purchase_order(osv.osv):
    _name = "purchase.order"
    _inherit = "purchase.order"
    
    def _calc_amount(self, cr, uid, ids, prop, unknow_none, unknow_dict):
        res = {}
        for order in self.browse(cr, uid, ids):
            res[order.id] = 0
            for oline in order.order_line:
                res[order.id] += oline.price_unit * oline.product_qty / oline.price_unit_id.coefficient
        return res

    def _amount_all(self, cr, uid, ids, field_name, arg, context):
        res = {}
        cur_obj=self.pool.get('res.currency')
        for order in self.browse(cr, uid, ids):
            res[order.id] = {
                'amount_untaxed': 0.0,
                'amount_tax': 0.0,
                'amount_total': 0.0,
            }
            val = val1 = 0.0
            cur=order.pricelist_id.currency_id
            for line in order.order_line:
                for c in self.pool.get('account.tax').compute(cr, uid, line.taxes_id, line.price_unit, line.product_qty, order.partner_address_id.id, line.product_id, order.partner_id):
                    val+= c['amount'] / line.price_unit_id.coefficient
                val1 += line.price_subtotal
            res[order.id]['amount_tax']=cur_obj.round(cr, uid, cur, val)
            res[order.id]['amount_untaxed']=cur_obj.round(cr, uid, cur, val1)
            res[order.id]['amount_total']=res[order.id]['amount_untaxed'] + res[order.id]['amount_tax']
        return res

    def _get_order(self, cr, uid, ids, context={}):
        result = {}
        for line in self.pool.get('purchase.order.line').browse(cr, uid, ids, context=context):
            result[line.order_id.id] = True
        return result.keys()

    _columns = {
        'amount_untaxed': fields.function(_amount_all, method=True, digits_compute= dp.get_precision('Purchase Price'), string='Untaxed Amount',
            store={
                'purchase.order.line': (_get_order, None, 10),
            }, multi="sums"),
        'amount_tax': fields.function(_amount_all, method=True, digits_compute= dp.get_precision('Purchase Price'), string='Taxes',
            store={
                'purchase.order.line': (_get_order, None, 10),
            }, multi="sums"),
        'amount_total': fields.function(_amount_all, method=True, digits_compute= dp.get_precision('Purchase Price'), string='Total',
            store={
                'purchase.order.line': (_get_order, None, 10),
            }, multi="sums"),
    }
    
    def inv_line_create(self, cr, uid, a, ol):
        result = super(purchase_order, self).inv_line_create(cr, uid, a, ol)
        result[2].update({'price_unit_id': ol.price_unit_id.id})
        return result
    
    def action_picking_create(self,cr, uid, ids, *args):
        picking_id = super(purchase_order, self).action_picking_create(cr, uid, ids, *args)
        move_obj = self.pool.get('stock.move')
        for order in self.browse(cr, uid, ids):
            for line in order.order_line:
                move_ids = move_obj.search(cr, uid, [('purchase_line_id','=',line.id),('picking_id','=',picking_id)])
                move_obj.write(cr, uid, move_ids, {
                                                   'price_unit_id': line.price_unit_id.id,
                                                   })
        return picking_id

purchase_order()

class purchase_order_line(osv.osv):
    _name = 'purchase.order.line'
    _inherit = 'purchase.order.line'

    def _get_price_unit_id(self, cr, uid, *args):
        cr.execute('select id from product_price_unit where coefficient = 1')
        res = cr.fetchone()
        return res and res[0] or False

    def _amount_line(self, cr, uid, ids, prop, unknow_none, unknow_dict):
        res = {}
        cur_obj=self.pool.get('res.currency')
        for line in self.browse(cr, uid, ids):
            cur = line.order_id.pricelist_id.currency_id
            res[line.id] = cur_obj.round(cr, uid, cur, line.price_unit * line.product_qty / line.price_unit_id.coefficient) 
        return res

    _columns = {
        'price_unit_id' : fields.many2one('product.price.unit','Price Unit', required=True),
        'price_subtotal': fields.function(_amount_line, method=True, string='Subtotal', digits_compute= dp.get_precision('Purchase Price')),
    }
    _defaults = {
        'price_unit_id': _get_price_unit_id,
    }

    def price_product_id_change(self, cr, uid, ids, pricelist, price_unit_id, product, qty, uom,
            partner_id, date_order=False, fiscal_position=False, date_planned=False,
            name=False, price_unit=False, notes=False):
        result = super(purchase_order_line, self).product_id_change(cr, uid, ids, pricelist, product, qty, uom,
            partner_id, date_order, fiscal_position, date_planned, name, price_unit, notes)
        if product and 'value' in result:
            pu = self.pool.get('product.product').browse(cr, uid, product)
            if pu.price_unit_id:
                result['value']['price_unit_id'] = pu.price_unit_id.id
        return result

purchase_order_line()

class stock_partial_picking(osv.osv_memory):
    _inherit = "stock.partial.picking"

    def view_init(self, cr, uid, fields_list, context=None):
        res = super(stock_partial_picking, self).view_init(cr, uid, fields_list, context=context)
        pick_obj = self.pool.get('stock.picking')        
        if not context:
            context={}
        moveids = []
        for pick in pick_obj.browse(cr, uid, context.get('active_ids', [])):            
            for m in pick.move_lines:
                if m.state in ('done', 'cancel'):
                    continue
                if 'move%s_product_id'%(m.id) not in self._columns:
                    self._columns['move%s_product_id'%(m.id)] = fields.many2one('product.product',string="Product")
                if 'move%s_product_qty'%(m.id) not in self._columns:
                    self._columns['move%s_product_qty'%(m.id)] = fields.float("Quantity")
                if 'move%s_product_uom'%(m.id) not in self._columns:
                    self._columns['move%s_product_uom'%(m.id)] = fields.many2one('product.uom',string="Product UOM")

                if (pick.type == 'in') and (m.product_id.cost_method == 'average'):
                    if 'move%s_product_price'%(m.id) not in self._columns:
                        self._columns['move%s_product_price'%(m.id)] = fields.float("Price")
                    if 'move%s_product_currency'%(m.id) not in self._columns:
                        self._columns['move%s_product_currency'%(m.id)] = fields.many2one('res.currency',string="Currency")
                    if 'move%s_product_price_unit_id'%(m.id) not in self._columns:
                        self._columns['move%s_product_price_unit_id'%(m.id)] = fields.float("Price Unit")
        return res   

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False,submenu=False):
        result = super(stock_partial_picking, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar,submenu)        
        pick_obj = self.pool.get('stock.picking')
        picking_ids = context.get('active_ids', False) 
        picking_ids = pick_obj.search(cr, uid, [('id', 'in', picking_ids)])               
        _moves_arch_lst = """<form string="Deliver Products">
                        <separator colspan="4" string="Delivery Information"/>
                        <field name="date" colspan="4" />
                        <field name="partner_id"/>
                        <field name="address_id"/>
                        <newline/>
                        <separator colspan="4" string="Move Detail"/>
                        """
        _moves_fields = result['fields']
        if picking_ids and view_type in ['form']:
            for pick in pick_obj.browse(cr, uid, picking_ids, context):
                for m in pick.move_lines:
                    if m.state in ('done', 'cancel'):
                        continue
                    _moves_fields.update({
                        'move%s_product_id'%(m.id)  : {
                                    'string': _('Product'),
                                    'type' : 'many2one', 
                                    'relation': 'product.product', 
                                    'required' : True, 
                                    'readonly' : True,                                    
                                    },
                        'move%s_product_qty'%(m.id) : {
                                    'string': _('Quantity'),
                                    'type' : 'float',
                                    'required': True,                                    
                                    },
                        'move%s_product_uom'%(m.id) : {
                                    'string': _('Product UOM'),
                                    'type' : 'many2one', 
                                    'relation': 'product.uom', 
                                    'required' : True, 
                                    'readonly' : True,                                    
                                    }
                    })                
                    
                    _moves_arch_lst += """
                        <group colspan="4" col="12">
                        <field name="move%s_product_id" nolabel="1"/>
                        <field name="move%s_product_qty" string="Qty" />
                        <field name="move%s_product_uom" nolabel="1" />
                    """%(m.id, m.id, m.id)
                    if (pick.type == 'in') and (m.product_id.cost_method == 'average'):                        
                        _moves_fields.update({
                            'move%s_product_price'%(m.id) : {
                                    'string': _('Price'),
                                    'type' : 'float',
                                    },
                            'move%s_product_currency'%(m.id): {
                                    'string': _('Currency'),
                                    'type' : 'many2one', 
                                    'relation': 'res.currency',
                                    },
                            'move%s_product_price_unit_id'%(m.id): {
                                    'string': _('Price Unit'),
                                    'type': 'many2one',
                                    'relation': 'product.price.unit', 
                                    'required': True,
                                    },
                        })
                        _moves_arch_lst += """
                            <field name="move%s_product_price" />
                            <field name="move%s_product_currency" nolabel="1"/>
                            <field name="move%s_product_price_unit_id" nolabel="1"/>
                        """%(m.id, m.id, m.id)
                    _moves_arch_lst += """
                        </group>
                        """
        _moves_arch_lst += """
                <separator string="" colspan="4" />
                <label string="" colspan="2"/>
                <group col="2" colspan="2">
                <button icon='gtk-cancel' special="cancel"
                    string="_Cancel" />
                <button name="do_partial" string="_Deliver"
                    colspan="1" type="object" icon="gtk-apply" />
            </group>                    
        </form>"""
        result['arch'] = _moves_arch_lst
        result['fields'] = _moves_fields           
        return result

    def default_get(self, cr, uid, fields, context=None):
        """ 
             To get default values for the object.
            
             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param fields: List of fields for which we want default values 
             @param context: A standard dictionary 
             
             @return: A dictionary which of fields with values. 
        
        """ 

        res = super(stock_partial_picking, self).default_get(cr, uid, fields, context=context)
        pick_obj = self.pool.get('stock.picking')        
        if not context:
            context={}
        moveids = []
        if 'date' in fields:
            res.update({'date': time.strftime('%Y-%m-%d %H:%M:%S')})
        for pick in pick_obj.browse(cr, uid, context.get('active_ids', [])):
            if 'partner_id' in fields:
                res.update({'partner_id': pick.address_id.partner_id.id})                
            if 'address_id' in fields:
                res.update({'address_id': pick.address_id.id})            
            for m in pick.move_lines:
                if m.state in ('done', 'cancel'):
                    continue
                if 'move%s_product_id'%(m.id) in fields:
                    res['move%s_product_id'%(m.id)] = m.product_id.id
                if 'move%s_product_qty'%(m.id) in fields:
                    res['move%s_product_qty'%(m.id)] = m.product_qty
                if 'move%s_product_uom'%(m.id) in fields:
                    res['move%s_product_uom'%(m.id)] = m.product_uom.id

                if (pick.type == 'in') and (m.product_id.cost_method == 'average'):
                    price = 0
                    if hasattr(m, 'purchase_line_id') and m.purchase_line_id:
                        price = m.purchase_line_id.price_unit
                    if hasattr(m, 'purchase_line_id') and m.price_unit_id:
                        price_unit_id = m.purchase_line_id.price_unit_id.id

                    currency = False
                    if hasattr(pick, 'purchase_id') and pick.purchase_id:
                        currency = pick.purchase_id.pricelist_id.currency_id.id
        
                    if 'move%s_product_price'%(m.id) in fields:
                        res['move%s_product_price'%(m.id)] = price
                    if 'move%s_product_currency'%(m.id) in fields:
                        res['move%s_product_currency'%(m.id)] = currency
                    if 'move%s_product_price_unit_id'%(m.id) in fields:
                        res['move%s_product_price_unit_id'%(m.id)] = price_unit_id
        return res   

    def do_partial(self, cr, uid, ids, context):    
        pick_obj = self.pool.get('stock.picking')    
        picking_ids = context.get('active_ids', False)
        partial = self.browse(cr, uid, ids[0], context)
        partial_datas = {
            'partner_id' : partial.partner_id and partial.partner_id.id or False,
            'address_id' : partial.address_id and partial.address_id.id or False,
            'delivery_date' : partial.date         
        }
        for pick in pick_obj.browse(cr, uid, picking_ids):
            for m in pick.move_lines:
                if m.state in ('done', 'cancel'):
                    continue
                partial_datas['move%s'%(m.id)] = {
                    'product_id' : getattr(partial, 'move%s_product_id'%(m.id)).id,
                    'product_qty' : getattr(partial, 'move%s_product_qty'%(m.id)),
                    'product_uom' : getattr(partial, 'move%s_product_uom'%(m.id)).id
                }

                if (pick.type == 'in') and (m.product_id.cost_method == 'average'):   
                    partial_datas['move%s'%(m.id)].update({             
                        'product_price' : getattr(partial, 'move%s_product_price'%(m.id)),
                        'product_currency': getattr(partial, 'move%s_product_currency'%(m.id)).id,
                        'product_price_unit_id' : getattr(partial, 'move%s_product_price_unit_id'%(m.id)).id,
                    })          
        res = pick_obj.do_partial(cr, uid, picking_ids, partial_datas, context=context)
        return {}
 
stock_partial_picking()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
