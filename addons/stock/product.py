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

from osv import fields, osv
from tools.translate import _
import decimal_precision as dp

class product_product(osv.osv):
    _inherit = "product.product"

    def get_product_accounts(self, cr, uid, product_id, context=None):
        """ To get the stock input account, stock output account and stock journal related to product.
        @param product_id: product id
        @return: dictionary which contains information regarding stock input account, stock output account and stock journal
        """
        if context is None:
            context = {}
        product_obj = self.pool.get('product.product').browse(cr, uid, product_id, context=context)

        stock_input_acc = product_obj.property_stock_account_input and product_obj.property_stock_account_input.id or False
        if not stock_input_acc:
            stock_input_acc = product_obj.categ_id.property_stock_account_input_categ and product_obj.categ_id.property_stock_account_input_categ.id or False

        stock_output_acc = product_obj.property_stock_account_output and product_obj.property_stock_account_output.id or False
        if not stock_output_acc:
            stock_output_acc = product_obj.categ_id.property_stock_account_output_categ and product_obj.categ_id.property_stock_account_output_categ.id or False

        journal_id = product_obj.categ_id.property_stock_journal and product_obj.categ_id.property_stock_journal.id or False
        account_variation = product_obj.categ_id.property_stock_variation and product_obj.categ_id.property_stock_variation.id or False

        return {
            'stock_account_input': stock_input_acc,
            'stock_account_output': stock_output_acc,
            'stock_journal': journal_id,
            'property_stock_variation': account_variation
        }

    def do_change_standard_price(self, cr, uid, ids, datas, context=None):
        """ Changes the Standard Price of Product and creates an account move accordingly.
        @param datas : dict. contain default datas like new_price, stock_output_account, stock_input_account, stock_journal
        @param context: A standard dictionary
        @return:

        """
        location_obj = self.pool.get('stock.location')
        move_obj = self.pool.get('account.move')
        move_line_obj = self.pool.get('account.move.line')
        if context is None:
            context = {}

        new_price = datas.get('new_price', 0.0)
        stock_output_acc = datas.get('stock_output_account', False)
        stock_input_acc = datas.get('stock_input_account', False)
        journal_id = datas.get('stock_journal', False)
        product_obj=self.browse(cr, uid, ids, context=context)[0]
        account_variation = product_obj.categ_id.property_stock_variation
        account_variation_id = account_variation and account_variation.id or False
        if not account_variation_id: raise osv.except_osv(_('Error!'), _('Variation Account is not specified for Product Category: %s') % (product_obj.categ_id.name))
        move_ids = []
        loc_ids = location_obj.search(cr, uid,[('usage','=','internal')])
        for rec_id in ids:
            for location in location_obj.browse(cr, uid, loc_ids, context=context):
                c = context.copy()
                c.update({
                    'location': location.id,
                    'compute_child': False
                })

                product = self.browse(cr, uid, rec_id, context=c)
                qty = product.qty_available
                diff = product.standard_price - new_price
                if not diff: raise osv.except_osv(_('Error!'), _("Could not find any difference between standard price and new price!"))
                if qty:
                    company_id = location.company_id and location.company_id.id or False
                    if not company_id: raise osv.except_osv(_('Error!'), _('Company is not specified in Location'))
                    #
                    # Accounting Entries
                    #
                    if not journal_id:
                        journal_id = product.categ_id.property_stock_journal and product.categ_id.property_stock_journal.id or False
                    if not journal_id:
                        raise osv.except_osv(_('Error!'),
                            _('There is no journal defined '\
                                'on the product category: "%s" (id: %d)') % \
                                (product.categ_id.name,
                                    product.categ_id.id,))
                    move_id = move_obj.create(cr, uid, {
                                'journal_id': journal_id,
                                'company_id': company_id
                                })

                    move_ids.append(move_id)


                    if diff > 0:
                        if not stock_input_acc:
                            stock_input_acc = product.product_tmpl_id.\
                                property_stock_account_input.id
                        if not stock_input_acc:
                            stock_input_acc = product.categ_id.\
                                    property_stock_account_input_categ.id
                        if not stock_input_acc:
                            raise osv.except_osv(_('Error!'),
                                    _('There is no stock input account defined ' \
                                            'for this product: "%s" (id: %d)') % \
                                            (product.name,
                                                product.id,))
                        amount_diff = qty * diff
                        move_line_obj.create(cr, uid, {
                                    'name': product.name,
                                    'account_id': stock_input_acc,
                                    'debit': amount_diff,
                                    'move_id': move_id,
                                    })
                        move_line_obj.create(cr, uid, {
                                    'name': product.categ_id.name,
                                    'account_id': account_variation_id,
                                    'credit': amount_diff,
                                    'move_id': move_id
                                    })
                    elif diff < 0:
                        if not stock_output_acc:
                            stock_output_acc = product.product_tmpl_id.\
                                property_stock_account_output.id
                        if not stock_output_acc:
                            stock_output_acc = product.categ_id.\
                                    property_stock_account_output_categ.id
                        if not stock_output_acc:
                            raise osv.except_osv(_('Error!'),
                                    _('There is no stock output account defined ' \
                                            'for this product: "%s" (id: %d)') % \
                                            (product.name,
                                                product.id,))
                        amount_diff = qty * -diff
                        move_line_obj.create(cr, uid, {
                                        'name': product.name,
                                        'account_id': stock_output_acc,
                                        'credit': amount_diff,
                                        'move_id': move_id
                                    })
                        move_line_obj.create(cr, uid, {
                                        'name': product.categ_id.name,
                                        'account_id': account_variation_id,
                                        'debit': amount_diff,
                                        'move_id': move_id
                                    })

            self.write(cr, uid, rec_id, {'standard_price': new_price})

        return move_ids

    def view_header_get(self, cr, user, view_id, view_type, context=None):
        if context is None:
            context = {}
        res = super(product_product, self).view_header_get(cr, user, view_id, view_type, context)
        if res: return res
        if (context.get('active_id', False)) and (context.get('active_model') == 'stock.location'):
            return _('Products: ')+self.pool.get('stock.location').browse(cr, user, context['active_id'], context).name
        return res

    def get_product_available(self, cr, uid, ids, context=None):
        """ Finds whether product is available or not in particular warehouse.
        @return: Dictionary of values
        """
        if context is None:
            context = {}
        
        location_obj = self.pool.get('stock.location')
        warehouse_obj = self.pool.get('stock.warehouse')
        
        states = context.get('states',[])
        what = context.get('what',())
        if not ids:
            ids = self.search(cr, uid, [])
        res = {}.fromkeys(ids, 0.0)
        if not ids:
            return res

    # TODO: write in more ORM way, less queries, more pg84 magic
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
            elif type(context['location']) in (type(''), type(u'')):
                location_ids = location_obj.search(cr, uid, [('name','ilike',context['location'])], context=context)
            else:
                location_ids = context['location']
        else:
            location_ids = []
            wids = warehouse_obj.search(cr, uid, [], context=context)
            for w in warehouse_obj.browse(cr, uid, wids, context=context):
                location_ids.append(w.lot_stock_id.id)

        # build the list of ids of children of the location given by id
        if context.get('compute_child',True):
            child_location_ids = location_obj.search(cr, uid, [('location_id', 'child_of', location_ids)])
            location_ids = child_location_ids or location_ids
        else:
            location_ids = location_ids

        uoms_o = {}
        product2uom = {}
        for product in self.browse(cr, uid, ids, context=context):
            product2uom[product.id] = product.uom_id.id
            uoms_o[product.uom_id.id] = product.uom_id

        results = []
        results2 = []

        from_date = context.get('from_date',False)
        to_date = context.get('to_date',False)
        date_str = False
        date_values = False
        where = [tuple(location_ids),tuple(location_ids),tuple(ids),tuple(states)]
        if from_date and to_date:
            date_str = "date>=%s and date<=%s"
            where.append(tuple([from_date]))
            where.append(tuple([to_date]))
        elif from_date:
            date_str = "date>=%s"
            date_values = [from_date]
        elif to_date:
            date_str = "date<=%s"
            date_values = [to_date]

        prodlot_id = context.get('prodlot_id', False)

    # TODO: perhaps merge in one query.
        if date_values:
            where.append(tuple(date_values))
        if 'in' in what:
            # all moves from a location out of the set to a location in the set
            cr.execute(
                'select sum(product_qty), product_id, product_uom '\
                'from stock_move '\
                'where location_id NOT IN %s '\
                'and location_dest_id IN %s '\
                'and product_id IN %s '\
                '' + (prodlot_id and ('and prodlot_id = ' + str(prodlot_id)) or '') + ' '\
                'and state IN %s ' + (date_str and 'and '+date_str+' ' or '') +' '\
                'group by product_id,product_uom',tuple(where))
            results = cr.fetchall()
        if 'out' in what:
            # all moves from a location in the set to a location out of the set
            cr.execute(
                'select sum(product_qty), product_id, product_uom '\
                'from stock_move '\
                'where location_id IN %s '\
                'and location_dest_id NOT IN %s '\
                'and product_id  IN %s '\
                '' + (prodlot_id and ('and prodlot_id = ' + str(prodlot_id)) or '') + ' '\
                'and state in %s ' + (date_str and 'and '+date_str+' ' or '') + ' '\
                'group by product_id,product_uom',tuple(where))
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
        #TOCHECK: before change uom of product, stock move line are in old uom.
        context.update({'raise-exception': False})
        for amount, prod_id, prod_uom in results:
            amount = uom_obj._compute_qty_obj(cr, uid, uoms_o[prod_uom], amount,
                     uoms_o[context.get('uom', False) or product2uom[prod_id]], context=context)
            res[prod_id] += amount
        for amount, prod_id, prod_uom in results2:
            amount = uom_obj._compute_qty_obj(cr, uid, uoms_o[prod_uom], amount,
                    uoms_o[context.get('uom', False) or product2uom[prod_id]], context=context)
            res[prod_id] -= amount
        return res

    def _product_available(self, cr, uid, ids, field_names=None, arg=False, context=None):
        """ Finds the incoming and outgoing quantity of product.
        @return: Dictionary of values
        """
        if not field_names:
            field_names = []
        if context is None:
            context = {}
        res = {}
        for id in ids:
            res[id] = {}.fromkeys(field_names, 0.0)
        for f in field_names:
            c = context.copy()
            if f == 'qty_available':
                c.update({ 'states': ('done',), 'what': ('in', 'out') })
            if f == 'virtual_available':
                c.update({ 'states': ('confirmed','waiting','assigned','done'), 'what': ('in', 'out') })
            if f == 'incoming_qty':
                c.update({ 'states': ('confirmed','waiting','assigned'), 'what': ('in',) })
            if f == 'outgoing_qty':
                c.update({ 'states': ('confirmed','waiting','assigned'), 'what': ('out',) })
            stock = self.get_product_available(cr, uid, ids, context=c)
            for id in ids:
                res[id][f] = stock.get(id, 0.0)
        return res

    _columns = {
        'qty_available': fields.function(_product_available, type='float', string='Quantity On Hand', help="Current quantities of products in selected locations or all internal if none have been selected.", multi='qty_available', digits_compute=dp.get_precision('Product UoM')),
        'virtual_available': fields.function(_product_available, type='float', string='Quantity On Order', help="Future stock for this product according to the selected locations or all internal if none have been selected. Computed as: Real Stock - Outgoing + Incoming.", multi='qty_available', digits_compute=dp.get_precision('Product UoM')),
        'incoming_qty': fields.function(_product_available, type='float', string='Incoming', help="Quantities of products that are planned to arrive in selected locations or all internal if none have been selected.", multi='qty_available', digits_compute=dp.get_precision('Product UoM')),
        'outgoing_qty': fields.function(_product_available, type='float', string='Outgoing', help="Quantities of products that are planned to leave in selected locations or all internal if none have been selected.", multi='qty_available', digits_compute=dp.get_precision('Product UoM')),
        'track_production': fields.boolean('Track Manufacturing Lots' , help="Forces to specify a Production Lot for all moves containing this product and generated by a Manufacturing Order"),
        'track_incoming': fields.boolean('Track Incoming Lots', help="Forces to specify a Production Lot for all moves containing this product and coming from a Supplier Location"),
        'track_outgoing': fields.boolean('Track Outgoing Lots', help="Forces to specify a Production Lot for all moves containing this product and going to a Customer Location"),
        'location_id': fields.dummy(string='Location', relation='stock.location', type='many2one'),
        'warehouse_id': fields.dummy(string='Warehouse', relation='stock.warehouse', type='many2one'),
        'valuation':fields.selection([('manual_periodic', 'Periodical (manual)'),
                                        ('real_time','Real Time (automated)'),], 'Inventory Valuation',
                                        help="If real-time valuation is enabled for a product, the system will automatically write journal entries corresponding to stock moves." \
                                             "The inventory variation account set on the product category will represent the current inventory value, and the stock input and stock output account will hold the counterpart moves for incoming and outgoing products."
                                        , required=True),
    }

    _defaults = {
        'valuation': lambda *a: 'manual_periodic',
    }

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super(product_product,self).fields_view_get(cr, uid, view_id, view_type, context, toolbar=toolbar, submenu=submenu)
        if context is None:
            context = {}
        if ('location' in context) and context['location']:
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
                    if fields.get('qty_available'):
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
            view_load=True,
            domain=[('usage','like','procurement')],
            help="For the current product, this stock location will be used, instead of the default one, as the source location for stock moves generated by procurements"),
        'property_stock_production': fields.property(
            'stock.location',
            type='many2one',
            relation='stock.location',
            string="Production Location",
            view_load=True,
            domain=[('usage','like','production')],
            help="For the current product, this stock location will be used, instead of the default one, as the source location for stock moves generated by production orders"),
        'property_stock_inventory': fields.property(
            'stock.location',
            type='many2one',
            relation='stock.location',
            string="Inventory Location",
            view_load=True,
            domain=[('usage','like','inventory')],
            help="For the current product, this stock location will be used, instead of the default one, as the source location for stock moves generated when you do an inventory"),
        'property_stock_account_input': fields.property('account.account',
            type='many2one', relation='account.account',
            string='Stock Input Account', view_load=True,
            help='When doing real-time inventory valuation, counterpart Journal Items for all incoming stock moves will be posted in this account. If not set on the product, the one from the product category is used.'),
        'property_stock_account_output': fields.property('account.account',
            type='many2one', relation='account.account',
            string='Stock Output Account', view_load=True,
            help='When doing real-time inventory valuation, counterpart Journal Items for all outgoing stock moves will be posted in this account. If not set on the product, the one from the product category is used.'),
    }

product_template()

class product_category(osv.osv):

    _inherit = 'product.category'
    _columns = {
        'property_stock_journal': fields.property('account.journal',
            relation='account.journal', type='many2one',
            string='Stock journal', view_load=True,
            help="When doing real-time inventory valuation, this is the Accounting Journal in which entries will be automatically posted when stock moves are processed."),
        'property_stock_account_input_categ': fields.property('account.account',
            type='many2one', relation='account.account',
            string='Stock Input Account', view_load=True,
            help='When doing real-time inventory valuation, counterpart Journal Items for all incoming stock moves will be posted in this account. This is the default value for all products in this category, it can also directly be set on each product.'),
        'property_stock_account_output_categ': fields.property('account.account',
            type='many2one', relation='account.account',
            string='Stock Output Account', view_load=True,
            help='When doing real-time inventory valuation, counterpart Journal Items for all outgoing stock moves will be posted in this account. This is the default value for all products in this category, it can also directly be set on each product.'),
        'property_stock_variation': fields.property('account.account',
            type='many2one',
            relation='account.account',
            string="Stock Variation Account",
            view_load=True,
            help="When real-time inventory valuation is enabled on a product, this account will hold the current value of the products.",),
    }

product_category()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
