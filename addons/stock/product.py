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

from osv import fields, osv
from tools.translate import _


class product_product(osv.osv):
    _inherit = "product.product"
    def view_header_get(self, cr, user, view_id, view_type, context):
        res = super(product_product, self).view_header_get(cr, user, view_id, view_type, context)
        if res: return res
        if (context.get('location', False)):
            return _('Products: ')+self.pool.get('stock.location').browse(cr, user, context['location'], context).name
        return res

    def get_product_available(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        states = context.get('states',[])
        what = context.get('what',())
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
            location_ids = []
            wids = self.pool.get('stock.warehouse').search(cr, uid, [], context=context)
            for w in self.pool.get('stock.warehouse').browse(cr, uid, wids, context=context):
                location_ids.append(w.lot_stock_id.id)

        # build the list of ids of children of the location given by id
        if context.get('compute_child',True):
            child_location_ids = self.pool.get('stock.location').search(cr, uid, [('location_id', 'child_of', location_ids)])
            location_ids = child_location_ids or location_ids
        else:
            location_ids = location_ids

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
        date_str = ''
        date_args = ()
        if from_date and to_date:
            date_str = "and date_planned>=%s and date_planned<=%s"
            date_args = (from_date, to_date)
        elif from_date:
            date_str = "and date_planned>=%s"
            date_args = (from_date,)
        elif to_date:
            date_str = "and date_planned<=%s"
            date_args = (to_date,)

        if 'in' in what:
            # all moves from a location out of the set to a location in the set
            cr.execute(
                'select sum(product_qty), product_id, product_uom '\
                'from stock_move '\
                'where location_id not in %s '\
                'and location_dest_id in %s '\
                'and product_id in %s '\
                'and state in %s '+ date_str + ' '\
                'group by product_id,product_uom',
                (tuple(location_ids), tuple(location_ids), tuple(ids),
                 tuple(states)) + date_args)
            results = cr.fetchall()
        if 'out' in what:
            # all moves from a location in the set to a location out of the set
            cr.execute(
                'select sum(product_qty), product_id, product_uom '\
                'from stock_move '\
                'where location_id in %s '\
                'and location_dest_id not in %s '\
                'and product_id in %s '\
                'and state in %s '+ date_str + ' '\
                'group by product_id,product_uom',
                (tuple(location_ids), tuple(location_ids), tuple(ids),
                 tuple(states)) + date_args)
            results2 = cr.fetchall()
        uom_obj = self.pool.get('product.uom')
        uoms = map(lambda x: x[2], results) + map(lambda x: x[2], results2)
        if context.get('uom', False):
            uoms += [context['uom']]

        uoms = filter(lambda x: x not in uoms_o.keys(), uoms)
        if uoms:
            uoms = uom_obj.browse(cr, uid, list(set(uoms)), context=context)
        for o in uoms:
            uoms_o[o.id] = o
        for amount, prod_id, prod_uom in results:
            amount = uom_obj._compute_qty_obj(cr, uid, uoms_o[prod_uom], amount,
                    uoms_o[context.get('uom', False) or product2uom[prod_id]])
            res[prod_id] += amount
        for amount, prod_id, prod_uom in results2:
            amount = uom_obj._compute_qty_obj(cr, uid, uoms_o[prod_uom], amount,
                    uoms_o[context.get('uom', False) or product2uom[prod_id]])
            res[prod_id] -= amount
        return res

    def _product_available(self, cr, uid, ids, field_names=None, arg=False, context={}):
        if not field_names:
            field_names=[]
        res = {}
        for id in ids:
            res[id] = {}.fromkeys(field_names, 0.0)
        for f in field_names:
            c = context.copy()
            if f=='qty_available':
                c.update({ 'states':('done',), 'what':('in', 'out') })
            if f=='virtual_available':
                c.update({ 'states':('confirmed','waiting','assigned','done'), 'what':('in', 'out') })
            if f=='incoming_qty':
                c.update({ 'states':('confirmed','waiting','assigned'), 'what':('in',) })
            if f=='outgoing_qty':
                c.update({ 'states':('confirmed','waiting','assigned'), 'what':('out',) })
            stock=self.get_product_available(cr,uid,ids,context=c)
            for id in ids:
                res[id][f] = stock.get(id, 0.0)
        return res

    _columns = {
        'qty_available': fields.function(_product_available, method=True, type='float', string='Real Stock', help="Current quantities of products in selected locations or all internal if none have been selected.", multi='qty_available'),
        'virtual_available': fields.function(_product_available, method=True, type='float', string='Virtual Stock', help="Futur stock for this product according to the selected location or all internal if none have been selected. Computed as: Real Stock - Outgoing + Incoming.", multi='qty_available'),
        'incoming_qty': fields.function(_product_available, method=True, type='float', string='Incoming', help="Quantities of products that are planned to arrive in selected locations or all internal if none have been selected.", multi='qty_available'),
        'outgoing_qty': fields.function(_product_available, method=True, type='float', string='Outgoing', help="Quantities of products that are planned to leave in selected locations or all internal if none have been selected.", multi='qty_available'),
        'track_production' : fields.boolean('Track Production Lots' , help="Force to use a Production Lot during production order"),
        'track_incoming' : fields.boolean('Track Incoming Lots', help="Force to use a Production Lot during receptions"),
        'track_outgoing' : fields.boolean('Track Outgoing Lots', help="Force to use a Production Lot during deliveries"),
    }
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False):
        if not context:
            context = {}
        res = super(product_product,self).fields_view_get(cr, uid, view_id, view_type, context, toolbar)
        if context.get('location'):
            location_info = self.pool.get('stock.location').browse(cr, uid, context['location'])
            fields=res.get('fields',{})
            if fields:
                if location_info.usage == 'supplier':
                    if fields.get('virtual_available'):
                        res['fields']['virtual_available']['string'] = _('Future Receptions')
                    if fields.get('qty_available'):
                        res['fields']['qty_available']['string'] = _('Received Qty')

                if location_info.usage == 'internal':
                    if fields.get('virtual_available'):
                        res['fields']['virtual_available']['string'] = _('Future Stock')

                if location_info.usage == 'customer':
                    if fields.get('virtual_available'):
                        res['fields']['virtual_available']['string'] = _('Future Deliveries')
                    if fields.get('qty_available'):
                        res['fields']['qty_available']['string'] = _('Delivered Qty')

                if location_info.usage == 'inventory':
                    if fields.get('virtual_available'):
                        res['fields']['virtual_available']['string'] = _('Future P&L')
                    res['fields']['qty_available']['string'] = _('P&L Qty')

                if location_info.usage == 'procurement':
                    if fields.get('virtual_available'):
                        res['fields']['virtual_available']['string'] = _('Future Qty')
                    if fields.get('qty_available'):
                        res['fields']['qty_available']['string'] = _('Unplanned Qty')

                if location_info.usage == 'production':
                    if fields.get('virtual_available'):
                        res['fields']['virtual_available']['string'] = _('Future Productions')
                    if fields.get('qty_available'):
                        res['fields']['qty_available']['string'] = _('Produced Qty')

        return res
product_product()


class product_template(osv.osv):
    _name = 'product.template'
    _inherit = 'product.template'
    _columns = {
        'property_stock_procurement': fields.property(
            'stock.location',
            type='many2one',
            relation='stock.location',
            string="Procurement Location",
            method=True,
            view_load=True,
            help="For the current product (template), this stock location will be used, instead of the default one, as the source location for stock moves generated by procurements"),
        'property_stock_production': fields.property(
            'stock.location',
            type='many2one',
            relation='stock.location',
            string="Production Location",
            method=True,
            view_load=True,
            help="For the current product (template), this stock location will be used, instead of the default one, as the source location for stock moves generated by production orders"),
        'property_stock_inventory': fields.property(
            'stock.location',
            type='many2one',
            relation='stock.location',
            string="Inventory Location",
            method=True,
            view_load=True,
            help="For the current product (template), this stock location will be used, instead of the default one, as the source location for stock moves generated when you do an inventory"),
        'property_stock_account_input': fields.property('account.account',
            type='many2one', relation='account.account',
            string='Stock Input Account', method=True, view_load=True,
            help='This account will be used, instead of the default one, to value input stock'),
        'property_stock_account_output': fields.property('account.account',
            type='many2one', relation='account.account',
            string='Stock Output Account', method=True, view_load=True,
            help='This account will be used, instead of the default one, to value output stock'),
    }

product_template()


class product_category(osv.osv):
    _inherit = 'product.category'
    _columns = {
        'property_stock_journal': fields.property('account.journal',
            relation='account.journal', type='many2one',
            string='Stock journal', method=True, view_load=True,
            help="This journal will be used for the accounting move generated by stock move"),
        'property_stock_account_input_categ': fields.property('account.account',
            type='many2one', relation='account.account',
            string='Stock Input Account', method=True, view_load=True,
            help='This account will be used to value the input stock'),
        'property_stock_account_output_categ': fields.property('account.account',
            type='many2one', relation='account.account',
            string='Stock Output Account', method=True, view_load=True,
            help='This account will be used to value the output stock'),
    }

product_category()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

