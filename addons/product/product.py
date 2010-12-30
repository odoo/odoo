# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import osv, fields
import pooler

import math
from _common import rounding

from tools import config
from tools.translate import _

def is_pair(x):
    return not x%2

#----------------------------------------------------------
# UOM
#----------------------------------------------------------

class product_uom_categ(osv.osv):
    _name = 'product.uom.categ'
    _description = 'Product uom categ'
    _columns = {
        'name': fields.char('Name', size=64, required=True, translate=True),
    }
product_uom_categ()

class product_uom(osv.osv):
    _name = 'product.uom'
    _description = 'Product Unit of Measure'

    def _factor(self, cursor, user, ids, name, arg, context):
        res = {}
        for uom in self.browse(cursor, user, ids, context=context):
            if uom.factor:
                if uom.factor_inv_data:
                    res[uom.id] = uom.factor_inv_data
                else:
                    res[uom.id] = round(1 / uom.factor, 6)
            else:
                res[uom.id] = 0.0
        return res

    def _factor_inv(self, cursor, user, id, name, value, arg, context):
        ctx = context.copy()
        if 'read_delta' in ctx:
            del ctx['read_delta']
        if value:
            data = 0.0
            if round(1 / round(1/value, 6), 6) != value:
                data = value
            self.write(cursor, user, id, {
                'factor': round(1/value, 6),
                'factor_inv_data': data,
                }, context=ctx)
        else:
            self.write(cursor, user, id, {
                'factor': 0.0,
                'factor_inv_data': 0.0,
                }, context=ctx)

    _columns = {
        'name': fields.char('Name', size=64, required=True, translate=True),
        'category_id': fields.many2one('product.uom.categ', 'UoM Category', required=True, ondelete='cascade',
            help="Unit of Measure of a category can be converted between each others in the same category."),
        'factor': fields.float('Rate', digits=(12, 6), required=True,
            help='The coefficient for the formula:\n' \
                    '1 (base unit) = coeff (this unit). Rate = 1 / Factor.'),
        'factor_inv': fields.function(_factor, digits=(12, 6),
            method=True, string='Factor',
            help='The coefficient for the formula:\n' \
                    'coeff (base unit) = 1 (this unit). Factor = 1 / Rate.'),
        'factor_inv_data': fields.float('Factor', digits=(12, 6)),
        'rounding': fields.float('Rounding Precision', digits=(16, 3), required=True,
            help="The computed quantity will be a multiple of this value. Use 1.0 for products that can not be split."),
        'active': fields.boolean('Active'),
    }

    _defaults = {
        'factor': lambda *a: 1.0,
        'factor_inv': lambda *a: 1.0,
        'active': lambda *a: 1,
        'rounding': lambda *a: 0.01,
    }

    def _compute_qty(self, cr, uid, from_uom_id, qty, to_uom_id=False):
        if not from_uom_id or not qty or not to_uom_id:
            return qty
        uoms = self.browse(cr, uid, [from_uom_id, to_uom_id])
        if uoms[0].id == from_uom_id:
            from_unit, to_unit = uoms[0], uoms[-1]
        else:
            from_unit, to_unit = uoms[-1], uoms[0]
        return self._compute_qty_obj(cr, uid, from_unit, qty, to_unit)

    def _compute_qty_obj(self, cr, uid, from_unit, qty, to_unit, context={}):
        if from_unit.category_id.id <> to_unit.category_id.id:
#            raise osv.except_osv(_('Warning !'),_('Conversion from Product UoM %s to Default UoM %s is not possible as they both belong to different Category!')% (from_unit.name,to_unit.name))
            return qty
        if from_unit.factor_inv_data:
            amount = qty * from_unit.factor_inv_data
        else:
            amount = qty / from_unit.factor
        if to_unit:
            if to_unit.factor_inv_data:
                amount = rounding(amount / to_unit.factor_inv_data, to_unit.rounding)
            else:
                amount = rounding(amount * to_unit.factor, to_unit.rounding)
        return amount

    def _compute_price(self, cr, uid, from_uom_id, price, to_uom_id=False):
        if not from_uom_id or not price or not to_uom_id:
            return price
        uoms = self.browse(cr, uid, [from_uom_id, to_uom_id])
        if uoms[0].id == from_uom_id:
            from_unit, to_unit = uoms[0], uoms[-1]
        else:
            from_unit, to_unit = uoms[-1], uoms[0]
        if from_unit.category_id.id <> to_unit.category_id.id:
#            raise osv.except_osv(_('Warning !'),_('Conversion from Product UoM %s to Default UoM %s is not possible as they both belong to different Category!')% (from_unit.name,to_unit.name))
            return price
        if from_unit.factor_inv_data:
            amount = price / from_unit.factor_inv_data
        else:
            amount = price * from_unit.factor
        if to_uom_id:
            if to_unit.factor_inv_data:
                amount = amount * to_unit.factor_inv_data
            else:
                amount = amount / to_unit.factor
        return amount

    def onchange_factor_inv(self, cursor, user, ids, value):
        if value == 0.0:
            return {'value': {'factor': 0}}
        return {'value': {'factor': round(1/value, 6)}}

    def onchange_factor(self, cursor, user, ids, value):
        if value == 0.0:
            return {'value': {'factor_inv': 0}}
        return {'value': {'factor_inv': round(1/value, 6)}}

product_uom()


class product_ul(osv.osv):
    _name = "product.ul"
    _description = "Shipping Unit"
    _columns = {
        'name' : fields.char('Name', size=64,select=True, required=True, translate=True),
        'type' : fields.selection([('unit','Unit'),('pack','Pack'),('box', 'Box'), ('palet', 'Pallet')], 'Type', required=True),
    }
product_ul()


#----------------------------------------------------------
# Categories
#----------------------------------------------------------
class product_category(osv.osv):

    def name_get(self, cr, uid, ids, context=None):
        if not len(ids):
            return []
        reads = self.read(cr, uid, ids, ['name','parent_id'], context)
        res = []
        for record in reads:
            name = record['name']
            if record['parent_id']:
                name = record['parent_id'][1]+' / '+name
            res.append((record['id'], name))
        return res

    def _name_get_fnc(self, cr, uid, ids, prop, unknow_none, context):
        res = self.name_get(cr, uid, ids, context)
        return dict(res)

    _name = "product.category"
    _description = "Product Category"
    _columns = {
        'name': fields.char('Name', size=64, required=True, translate=True),
        'complete_name': fields.function(_name_get_fnc, method=True, type="char", string='Name'),
        'parent_id': fields.many2one('product.category','Parent Category', select=True),
        'child_id': fields.one2many('product.category', 'parent_id', string='Child Categories'),
        'sequence': fields.integer('Sequence'),
    }
    _order = "sequence"
    def _check_recursion(self, cr, uid, ids):
        level = 100
        while len(ids):
            cr.execute('select distinct parent_id from product_category where id in %s', (tuple(ids),))
            ids = filter(None, map(lambda x:x[0], cr.fetchall()))
            if not level:
                return False
            level -= 1
        return True

    _constraints = [
        (_check_recursion, 'Error ! You can not create recursive categories.', ['parent_id'])
    ]
    def child_get(self, cr, uid, ids):
        return [ids]

product_category()


#----------------------------------------------------------
# Products
#----------------------------------------------------------
class product_template(osv.osv):
    _name = "product.template"
    _description = "Product Template"
    def _calc_seller_delay(self, cr, uid, ids, name, arg, context={}):
        result = {}
        for product in self.browse(cr, uid, ids, context):
            if product.seller_ids:
                result[product.id] = product.seller_ids[0].delay
            else:
                result[product.id] = 1
        return result

    _columns = {
        'name': fields.char('Name', size=128, required=True, translate=True, select=True),
        'product_manager': fields.many2one('res.users','Product Manager'),
        'description': fields.text('Description',translate=True),
        'description_purchase': fields.text('Purchase Description',translate=True),
        'description_sale': fields.text('Sale Description',translate=True),
        'type': fields.selection([('product','Stockable Product'),('consu', 'Consumable'),('service','Service')], 'Product Type', required=True, help="Will change the way procurements are processed. Consumables are stockable products with infinite stock, or for use when you have no stock management in the system."),
        'supply_method': fields.selection([('produce','Produce'),('buy','Buy')], 'Supply method', required=True, help="Produce will generate production order or tasks, according to the product type. Purchase will trigger purchase orders when requested."),
        'sale_delay': fields.float('Customer Lead Time', help="This is the average time between the confirmation of the customer order and the delivery of the finished products. It's the time you promise to your customers."),
        'produce_delay': fields.float('Manufacturing Lead Time', help="Average time to produce this product. This is only for the production order and, if it is a multi-level bill of material, it's only for the level of this product. Different delays will be summed for all levels and purchase orders."),
        'procure_method': fields.selection([('make_to_stock','Make to Stock'),('make_to_order','Make to Order')], 'Procure Method', required=True, help="'Make to Stock': When needed, take from the stock or wait until re-supplying. 'Make to Order': When needed, purchase or produce for the procurement request."),
        'rental': fields.boolean('Rentable Product'),
        'categ_id': fields.many2one('product.category','Category', required=True, change_default=True),
        'list_price': fields.float('Sale Price', digits=(16, int(config['price_accuracy'])), help="Base price for computing the customer price. Sometimes called the catalog price."),
        'standard_price': fields.float('Cost Price', required=True, digits=(16, int(config['price_accuracy'])), help="The cost of the product for accounting stock valuation. It can serves as a base price for supplier price."),
        'volume': fields.float('Volume', help="The volume in m3."),
        'weight': fields.float('Gross weight', help="The gross weight in Kg."),
        'weight_net': fields.float('Net weight', help="The net weight in Kg."),
        'cost_method': fields.selection([('standard','Standard Price'), ('average','Average Price')], 'Costing Method', required=True,
            help="Standard Price: the cost price is fixed and recomputed periodically (usually at the end of the year), Average Price: the cost price is recomputed at each reception of products."),
        'warranty': fields.float('Warranty (months)'),
        'sale_ok': fields.boolean('Can be sold', help="Determine if the product can be visible in the list of product within a selection from a sale order line."),
        'purchase_ok': fields.boolean('Can be Purchased', help="Determine if the product is visible in the list of products within a selection from a purchase order line."),
        'state': fields.selection([('',''),('draft', 'In Development'),('sellable','In Production'),('end','End of Lifecycle'),('obsolete','Obsolete')], 'Status', help="Tells the user if he can use the product or not."),
        'uom_id': fields.many2one('product.uom', 'Default UoM', required=True, help="Default Unit of Measure used for all stock operation."),
        'uom_po_id': fields.many2one('product.uom', 'Purchase UoM', required=True, help="Default Unit of Measure used for purchase orders. It must in the same category than the default unit of measure."),
        'uos_id' : fields.many2one('product.uom', 'Unit of Sale',
            help='Used by companies that manages two unit of measure: invoicing and stock management. For example, in food industries, you will manage a stock of ham but invoice in Kg. Keep empty to use the default UOM.'),
        'uos_coeff': fields.float('UOM -> UOS Coeff', digits=(16,4),
            help='Coefficient to convert UOM to UOS\n'
            ' uos = uom * coeff'),
        'mes_type': fields.selection((('fixed', 'Fixed'), ('variable', 'Variable')), 'Measure Type', required=True),
        'seller_delay': fields.function(_calc_seller_delay, method=True, type='integer', string='Supplier Lead Time', help="This is the average delay in days between the purchase order confirmation and the reception of goods for this product and for the default supplier. It is used by the scheduler to order requests based on reordering delays."),
        'seller_ids': fields.one2many('product.supplierinfo', 'product_id', 'Partners'),
        'loc_rack': fields.char('Rack', size=16),
        'loc_row': fields.char('Row', size=16),
        'loc_case': fields.char('Case', size=16),
        'company_id': fields.many2one('res.company', 'Company'),
    }

    def _get_uom_id(self, cr, uid, *args):
        cr.execute('select id from product_uom order by id limit 1')
        res = cr.fetchone()
        return res and res[0] or False

    def _default_category(self, cr, uid, context={}):
        if 'categ_id' in context and context['categ_id']:
            return context['categ_id']
        return False

    def onchange_uom(self, cursor, user, ids, uom_id,uom_po_id):
        if uom_id and uom_po_id:
            uom_obj=self.pool.get('product.uom')
            uom=uom_obj.browse(cursor,user,[uom_id])[0]
            uom_po=uom_obj.browse(cursor,user,[uom_po_id])[0]
            if uom.category_id.id != uom_po.category_id.id:
                return {'value': {'uom_po_id': uom_id}}
        return False

    _defaults = {
        'company_id': lambda self, cr, uid, context: False, # Visible by all
        'type': lambda *a: 'product',
        'list_price': lambda *a: 1,
        'cost_method': lambda *a: 'standard',
        'supply_method': lambda *a: 'buy',
        'standard_price': lambda *a: 1,
        'sale_ok': lambda *a: 1,
        'sale_delay': lambda *a: 7,
        'produce_delay': lambda *a: 1,
        'purchase_ok': lambda *a: 1,
        'procure_method': lambda *a: 'make_to_stock',
        'uom_id': _get_uom_id,
        'uom_po_id': _get_uom_id,
        'uos_coeff' : lambda *a: 1.0,
        'mes_type' : lambda *a: 'fixed',
        'categ_id' : _default_category,
    }

    def _check_uom(self, cursor, user, ids):
        for product in self.browse(cursor, user, ids):
            if product.uom_id.category_id.id <> product.uom_po_id.category_id.id:
                return False
        return True

    def _check_uos(self, cursor, user, ids):
        for product in self.browse(cursor, user, ids):
            if product.uos_id \
                    and product.uos_id.category_id.id \
                    == product.uom_id.category_id.id:
                return False
        return True

    _constraints = [
        (_check_uos, 'Error: UOS must be in a different category than the UOM', ['uos_id']),
        (_check_uom, 'Error: The default UOM and the purchase UOM must be in the same category.', ['uom_id']),
    ]

    def name_get(self, cr, user, ids, context={}):
        if 'partner_id' in context:
            pass
        return super(product_template, self).name_get(cr, user, ids, context)

product_template()

class product_product(osv.osv):
    def view_header_get(self, cr, uid, view_id, view_type, context):
        res = super(product_product, self).view_header_get(cr, uid, view_id, view_type, context)
        if (context.get('categ_id', False)):
            return _('Products: ')+self.pool.get('product.category').browse(cr, uid, context['categ_id'], context).name
        return res

    def _product_price(self, cr, uid, ids, name, arg, context={}):
        res = {}
        quantity = context.get('quantity', 1) or 1.0
        pricelist = context.get('pricelist', False)
        if pricelist:
            for id in ids:
                try:
                    price = self.pool.get('product.pricelist').price_get(cr,uid,[pricelist], id, quantity, context=context)[pricelist]
                except:
                    price = 0.0
                res[id] = price
        for id in ids:
            res.setdefault(id, 0.0)
        return res

    def _get_product_available_func(states, what):
        def _product_available(self, cr, uid, ids, name, arg, context={}):
            return {}.fromkeys(ids, 0.0)
        return _product_available

    _product_qty_available = _get_product_available_func(('done',), ('in', 'out'))
    _product_virtual_available = _get_product_available_func(('confirmed','waiting','assigned','done'), ('in', 'out'))
    _product_outgoing_qty = _get_product_available_func(('confirmed','waiting','assigned'), ('out',))
    _product_incoming_qty = _get_product_available_func(('confirmed','waiting','assigned'), ('in',))

    def _product_lst_price(self, cr, uid, ids, name, arg, context=None):
        res = {}
        product_uom_obj = self.pool.get('product.uom')
        for id in ids:
            res.setdefault(id, 0.0)
        for product in self.browse(cr, uid, ids, context=context):
            if 'uom' in context:
                uom = product.uos_id or product.uom_id
                res[product.id] = product_uom_obj._compute_price(cr, uid,
                        uom.id, product.list_price, context['uom'])
            else:
                res[product.id] = product.list_price
            res[product.id] =  (res[product.id] or 0.0) * (product.price_margin or 1.0) + product.price_extra
        return res

    def _get_partner_code_name(self, cr, uid, ids, product_id, partner_id, context={}):
        product = self.browse(cr, uid, [product_id], context)[0]
        for supinfo in product.seller_ids:
            if supinfo.name.id == partner_id:
                return {'code': supinfo.product_code, 'name': supinfo.product_name}
        return {'code' : product.default_code, 'name' : product.name}

    def _product_code(self, cr, uid, ids, name, arg, context={}):
        res = {}
        for p in self.browse(cr, uid, ids, context):
            res[p.id] = self._get_partner_code_name(cr, uid, [], p.id, context.get('partner_id', None), context)['code']
        return res

    def _product_partner_ref(self, cr, uid, ids, name, arg, context={}):
        res = {}
        for p in self.browse(cr, uid, ids, context):
            data = self._get_partner_code_name(cr, uid, [], p.id, context.get('partner_id', None), context)
            if not data['code']:
                data['code'] = p.default_code
            if not data['name']:
                data['name'] = p.name
            res[p.id] = (data['code'] and ('['+data['code']+'] ') or '') + \
                    (data['name'] or '')
        return res

    _defaults = {
        'active': lambda *a: 1,
        'price_extra': lambda *a: 0.0,
        'price_margin': lambda *a: 1.0,
    }

    _name = "product.product"
    _description = "Product"
    _table = "product_product"
    _inherits = {'product.template': 'product_tmpl_id'}
    _columns = {
        'qty_available': fields.function(_product_qty_available, method=True, type='float', string='Real Stock'),
        'virtual_available': fields.function(_product_virtual_available, method=True, type='float', string='Virtual Stock'),
        'incoming_qty': fields.function(_product_incoming_qty, method=True, type='float', string='Incoming'),
        'outgoing_qty': fields.function(_product_outgoing_qty, method=True, type='float', string='Outgoing'),
        'price': fields.function(_product_price, method=True, type='float', string='Customer Price', digits=(16, int(config['price_accuracy']))),
        'lst_price' : fields.function(_product_lst_price, method=True, type='float', string='List Price', digits=(16, int(config['price_accuracy']))),
        'code': fields.function(_product_code, method=True, type='char', string='Code'),
        'partner_ref' : fields.function(_product_partner_ref, method=True, type='char', string='Customer ref'),
        'default_code' : fields.char('Code', size=64),
        'active': fields.boolean('Active'),
        'variants': fields.char('Variants', size=64),
        'product_tmpl_id': fields.many2one('product.template', 'Product Template', required=True),
        'ean13': fields.char('EAN13', size=13),
        'packaging' : fields.one2many('product.packaging', 'product_id', 'Logistical Units', help="Gives the different ways to package the same product. This has no impact on the packing order and is mainly used if you use the EDI module."),
        'price_extra': fields.float('Variant Price Extra', digits=(16, int(config['price_accuracy']))),
        'price_margin': fields.float('Variant Price Margin', digits=(16, int(config['price_accuracy']))),
    }

    def onchange_uom(self, cursor, user, ids, uom_id,uom_po_id):
        if uom_id and uom_po_id:
            uom_obj=self.pool.get('product.uom')
            uom=uom_obj.browse(cursor,user,[uom_id])[0]
            uom_po=uom_obj.browse(cursor,user,[uom_po_id])[0]
            if uom.category_id.id != uom_po.category_id.id:
                return {'value': {'uom_po_id': uom_id}}
        return False

    def _check_ean_key(self, cr, uid, ids):
        for partner in self.browse(cr, uid, ids):
            if not partner.ean13:
                continue
            if len(partner.ean13) <> 13:
                return False
            try:
                int(partner.ean13)
            except:
                return False
            sum=0
            for i in range(12):
                if is_pair(i):
                    sum += int(partner.ean13[i])
                else:
                    sum += 3 * int(partner.ean13[i])
            check = int(math.ceil(sum / 10.0) * 10 - sum)
            if check != int(partner.ean13[12]):
                return False
        return True

    _constraints = [(_check_ean_key, 'Error: Invalid ean code', ['ean13'])]

    def on_order(self, cr, uid, ids, orderline, quantity):
        pass

    def name_get(self, cr, user, ids, context={}):
        if not len(ids):
            return []
        def _name_get(d):
            #name = self._product_partner_ref(cr, user, [d['id']], '', '', context)[d['id']]
            #code = self._product_code(cr, user, [d['id']], '', '', context)[d['id']]
            name = d.get('name','')
            code = d.get('default_code',False)
            if code:
                name = '[%s] %s' % (code,name)
            if d['variants']:
                name = name + ' - %s' % (d['variants'],)
            return (d['id'], name)
        result = map(_name_get, self.read(cr, user, ids, ['variants','name','default_code'], context))
        return result

    def name_search(self, cr, user, name='', args=None, operator='ilike', context=None, limit=80):
        if not args:
            args=[]
        if not context:
            context={}
        if name:
            ids = self.search(cr, user, [('default_code','=',name)]+ args, limit=limit, context=context)
            if not len(ids):
                ids = self.search(cr, user, [('ean13','=',name)]+ args, limit=limit, context=context)
            if not len(ids):
                ids = self.search(cr, user, [('default_code',operator,name)]+ args, limit=limit, context=context)
                ids += self.search(cr, user, [('name',operator,name)]+ args, limit=limit, context=context)
        else:
            ids = self.search(cr, user, args, limit=limit, context=context)
        result = self.name_get(cr, user, ids, context)
        return result

    #
    # Could be overrided for variants matrices prices
    #
    def price_get(self, cr, uid, ids, ptype='list_price', context={}):
        res = {}
        product_uom_obj = self.pool.get('product.uom')

        for product in self.browse(cr, uid, ids, context=context):
            res[product.id] = product[ptype] or 0.0
            if ptype == 'list_price':
                res[product.id] = (res[product.id] * (product.price_margin or 1.0)) + \
                        product.price_extra
            if 'uom' in context:
                uom = product.uos_id or product.uom_id
                res[product.id] = product_uom_obj._compute_price(cr, uid,
                        uom.id, res[product.id], context['uom'])
        return res

    def copy(self, cr, uid, id, default=None, context=None):
        if not context:
            context={}

        if ('variant' in context) and context['variant']:
            fields = ['product_tmpl_id', 'active', 'variants', 'default_code',
                    'price_margin', 'price_extra']
            data = self.read(cr, uid, id, fields=fields, context=context)
            for f in fields:
                if f in default:
                    data[f] = default[f]
            data['product_tmpl_id'] = data.get('product_tmpl_id', False) \
                    and data['product_tmpl_id'][0]
            del data['id']
            return self.create(cr, uid, data)
        else:
            return super(product_product, self).copy(cr, uid, id, default=default,
                    context=context)
product_product()

class product_packaging(osv.osv):
    _name = "product.packaging"
    _description = "Packaging"
    _rec_name = 'ean'
    _order = "sequence"
    _columns = {
        'sequence': fields.integer('Sequence'),
        'name' : fields.char('Description', size=64),
        'qty' : fields.float('Quantity by Package',
            help="The total number of products you can put by palet or box."),
        'ul' : fields.many2one('product.ul', 'Type of Package', required=True),
        'ul_qty' : fields.integer('Package by layer'),
        'rows' : fields.integer('Number of Layer', required=True,
            help='The number of layer on a palet or box'),
        'product_id' : fields.many2one('product.product', 'Product', select=1, ondelete='cascade', required=True),
        'ean' : fields.char('EAN', size=14,
            help="The EAN code of the package unit."),
        'code' : fields.char('Code', size=14,
            help="The code of the transport unit."),
        'weight': fields.float('Total Package Weight',
            help='The weight of a full of products palet or box.'),
        'weight_ul': fields.float('Empty Package Weight',
            help='The weight of the empty UL'),
        'height': fields.float('Height', help='The height of the package'),
        'width': fields.float('Width', help='The width of the package'),
        'length': fields.float('Length', help='The length of the package'),
    }

    def _get_1st_ul(self, cr, uid, context={}):
        cr.execute('select id from product_ul order by id asc limit 1')
        res = cr.fetchone()
        return (res and res[0]) or False

    _defaults = {
        'rows' : lambda *a : 3,
        'sequence' : lambda *a : 1,
        'ul' : _get_1st_ul,
    }

product_packaging()


class product_supplierinfo(osv.osv):
    _name = "product.supplierinfo"
    _description = "Information about a product supplier"
    _columns = {
        'name' : fields.many2one('res.partner', 'Partner', required=True, ondelete='cascade', help="Supplier of this product"),
        'product_name': fields.char('Partner Product Name', size=128, help="Name of the product for this partner, will be used when printing a request for quotation. Keep empty to use the internal one."),
        'product_code': fields.char('Partner Product Code', size=64, help="Code of the product for this partner, will be used when printing a request for quotation. Keep empty to use the internal one."),
        'sequence' : fields.integer('Priority'),
        'qty' : fields.float('Minimal Quantity', required=True, help="The minimal quantity to purchase for this supplier, expressed in the default unit of measure."),
        'product_id' : fields.many2one('product.template', 'Product', required=True, ondelete='cascade', select=True),
        'delay' : fields.integer('Delivery Delay', required=True, help="Delay in days between the confirmation of the purchase order and the reception of the products in your warehouse. Used by the scheduler for automatic computation of the purchase order planning."),
        'pricelist_ids': fields.one2many('pricelist.partnerinfo', 'suppinfo_id', 'Supplier Pricelist'),
    }
    _defaults = {
        'qty': lambda *a: 0.0,
        'sequence': lambda *a: 1,
        'delay': lambda *a: 1,
    }
    _order = 'sequence'
product_supplierinfo()


class pricelist_partnerinfo(osv.osv):
    _name = 'pricelist.partnerinfo'
    _columns = {
        'name': fields.char('Description', size=64),
        'suppinfo_id': fields.many2one('product.supplierinfo', 'Partner Information', required=True, ondelete='cascade'),
        'min_quantity': fields.float('Quantity', required=True),
        'price': fields.float('Unit Price', required=True, digits=(16, int(config['price_accuracy']))),
    }
    _order = 'min_quantity asc'
pricelist_partnerinfo()



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

