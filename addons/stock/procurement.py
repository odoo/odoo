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

from openerp.osv import fields, osv
from openerp.tools.translate import _

from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.relativedelta import relativedelta
from datetime import datetime
import openerp

class procurement_group(osv.osv):
    _inherit = 'procurement.group'
    _columns = {
        'partner_id': fields.many2one('res.partner', 'Partner')
    }

class procurement_rule(osv.osv):
    _inherit = 'procurement.rule'

    def _get_action(self, cr, uid, context=None):
        result = super(procurement_rule, self)._get_action(cr, uid, context=context)
        return result + [('move', 'Move From Another Location')]

    _columns = {
        'location_id': fields.many2one('stock.location', 'Destination Location'),
        'location_src_id': fields.many2one('stock.location', 'Source Location',
            help="Source location is action=move"),
        'picking_type_id': fields.many2one('stock.picking.type', 'Picking Type', 
            help="Picking Type determines the way the picking should be shown in the view, reports, ...")
    }

class procurement_order(osv.osv):
    _inherit = "procurement.order"
    _columns = {
        'location_id': fields.many2one('stock.location', 'Destination Location'),
        'move_ids': fields.one2many('stock.move', 'procurement_id', 'Moves', help="Moves created by the procurement"),
        'move_dest_id': fields.many2one('stock.move', 'Destination Move', help="Move which caused (created) the procurement"),
    }

    def _search_suitable_rule(self, cr, uid, procurement, domain, context=None):
        '''method overwritten in stock_location that is used to search the best suitable rule'''
        return self.pool.get('procurement.rule').search(cr, uid, domain, context=context)

    def _find_suitable_rule(self, cr, uid, procurement, context=None):
        rule_id = super(procurement_order, self)._find_suitable_rule(cr, uid, procurement, context=context)
        if not rule_id:
            rule_id = self._search_suitable_rule(cr, uid, procurement, [('location_id', '=', procurement.location_id.id)], context=context) #action=move
            rule_id = rule_id and rule_id[0] or False
        return rule_id

    def _run_move_create(self, cr, uid, procurement, context=None):
        return {
            'name': procurement.name,
            'company_id': procurement.company_id.id,
            'product_id': procurement.product_id.id,
            'date': procurement.date_planned,
            'date_expected': procurement.date_planned,
            'product_qty': procurement.product_qty,
            'product_uom': procurement.product_uom.id,
            'product_uom_qty': procurement.product_qty,
            'product_uos_qty': (procurement.product_uos and procurement.product_uos_qty)\
                    or procurement.product_qty,
            'product_uos': (procurement.product_uos and procurement.product_uos.id)\
                    or procurement.product_uom.id,
            'partner_id': procurement.group_id and procurement.group_id.partner_id and \
                    procurement.group_id.partner_id.id or False,
            'location_id': procurement.rule_id.location_src_id.id,
            'location_dest_id': procurement.rule_id.location_id.id,
            'move_dest_id': procurement.move_dest_id and procurement.move_dest_id.id or False,
            'procurement_id': procurement.id,
            'rule_id': procurement.rule_id.id,
            'origin': procurement.origin,
            'picking_type_id': procurement.rule_id.picking_type_id.id,
        }

    def _run(self, cr, uid, procurement, context=None):
        if procurement.rule_id and procurement.rule_id.action == 'move':
            if not procurement.rule_id.location_src_id:
                self.message_post(cr, uid, [procurement.id], body=_('No source location defined!'), context=context)
                return False
            move_obj = self.pool.get('stock.move')
            move_dict = self._run_move_create(cr, uid, procurement, context=context)
            move_id = move_obj.create(cr, uid, move_dict, context=context)
            move_obj.action_confirm(cr, uid, [move_id], context=context)
            return move_id
        return super(procurement_order, self)._run(cr, uid, procurement, context)

    def _check(self, cr, uid, procurement, context=None):
        if procurement.rule_id and procurement.rule_id.action == 'move':
            for move in procurement.move_ids:
                if not move.state in ('done', 'cancel'):
                    return False
            else:
                return True
        return super(procurement_order, self)._check(cr, uid, procurement, context)



    #
    # Scheduler
    # When stock is installed, it should also check for the different confirmed stock moves
    # if they can not be installed
    #
    #
    def run_scheduler(self, cr, uid, use_new_cursor=False, context=None):
        '''
        Call the scheduler in order to 

        @param self: The object pointer
        @param cr: The current row, from the database cursor,
        @param uid: The current user ID for security checks
        @param ids: List of selected IDs
        @param use_new_cursor: False or the dbname
        @param context: A standard dictionary for contextual values
        @return:  Dictionary of values
        '''

        super(procurement_order, self).run_scheduler(cr, uid, use_new_cursor=use_new_cursor, context=context)
        if context is None:
            context = {}
        try:
            if use_new_cursor:
                cr = openerp.registry(use_new_cursor).db.cursor()

            company = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id
            move_obj = self.pool.get('stock.move')
            #Minimum stock rules
            self. _procure_orderpoint_confirm(cr, uid, automatic=False,use_new_cursor=False, context=context, user_id=False)

            #Search all confirmed stock_moves and try to assign them
            confirmed_ids = move_obj.search(cr, uid, [('state', '=', 'confirmed'), ('company_id','=', company.id)], limit = None, context=context) #Type  = stockable product?
            for x in xrange(0, len(confirmed_ids), 100):
                move_obj.action_assign(cr, uid, confirmed_ids[x:x+100], context=context)
                if use_new_cursor:
                    cr.commit()
            
            
            if use_new_cursor:
                cr.commit()
        finally:
            if use_new_cursor:
                try:
                    cr.close()
                except Exception:
                    pass
        return {}

    def _prepare_automatic_op_procurement(self, cr, uid, product, warehouse, location_id, context=None):
        return {'name': _('Automatic OP: %s') % (product.name,),
                'origin': _('SCHEDULER'),
                'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                'product_id': product.id,
                'product_qty': -product.virtual_available,
                'product_uom': product.uom_id.id,
                'location_id': location_id,
                'company_id': warehouse.company_id.id,
                }

    def create_automatic_op(self, cr, uid, context=None):
        """
        Create procurement of  virtual stock < 0

        @param self: The object pointer
        @param cr: The current row, from the database cursor,
        @param uid: The current user ID for security checks
        @param context: A standard dictionary for contextual values
        @return:  Dictionary of values
        """
        if context is None:
            context = {}
        product_obj = self.pool.get('product.product')
        proc_obj = self.pool.get('procurement.order')
        warehouse_obj = self.pool.get('stock.warehouse')

        warehouse_ids = warehouse_obj.search(cr, uid, [], context=context)
        products_ids = product_obj.search(cr, uid, [], order='id', context=context)

        for warehouse in warehouse_obj.browse(cr, uid, warehouse_ids, context=context):
            context['warehouse'] = warehouse
            # Here we check products availability.
            # We use the method 'read' for performance reasons, because using the method 'browse' may crash the server.
            for product_read in product_obj.read(cr, uid, products_ids, ['virtual_available'], context=context):
                if product_read['virtual_available'] >= 0.0:
                    continue

                product = product_obj.browse(cr, uid, [product_read['id']], context=context)[0]
                if product.supply_method == 'buy':
                    location_id = warehouse.lot_stock_id.id
                elif product.supply_method == 'produce':
                    location_id = warehouse.lot_stock_id.id
                else:
                    continue
                proc_id = proc_obj.create(cr, uid,
                            self._prepare_automatic_op_procurement(cr, uid, product, warehouse, location_id, context=context),
                            context=context)
                self.assign(cr, uid, [proc_id])
                self.run(cr, uid, [proc_id])
        return True

    def _get_orderpoint_date_planned(self, cr, uid, orderpoint, start_date, context=None):
        date_planned = start_date + \
                       relativedelta(days=orderpoint.product_id.seller_delay or 0.0)
        return date_planned.strftime(DEFAULT_SERVER_DATE_FORMAT)

    def _prepare_orderpoint_procurement(self, cr, uid, orderpoint, product_qty, context=None):
        return {'name': orderpoint.name,
                'date_planned': self._get_orderpoint_date_planned(cr, uid, orderpoint, datetime.today(), context=context),
                'product_id': orderpoint.product_id.id,
                'product_qty': product_qty,
                'company_id': orderpoint.company_id.id,
                'product_uom': orderpoint.product_uom.id,
                'location_id': orderpoint.location_id.id,
                'origin': orderpoint.name}

    def _product_virtual_get(self, cr, uid, order_point):
        product_obj = self.pool.get('product.product')
        return product_obj._product_available(cr, uid,
                [order_point.product_id.id],
                {'location': order_point.location_id.id})[order_point.product_id.id]['virtual_available']

    def _procure_orderpoint_confirm(self, cr, uid, automatic=False,\
            use_new_cursor=False, context=None, user_id=False):
        '''
        Create procurement based on Orderpoint
        use_new_cursor: False or the dbname

        @param self: The object pointer
        @param cr: The current row, from the database cursor,
        @param user_id: The current user ID for security checks
        @param context: A standard dictionary for contextual values
        @param param: False or the dbname
        @return:  Dictionary of values
        """
        '''
        if context is None:
            context = {}
        if use_new_cursor:
            cr = openerp.registry(use_new_cursor).db.cursor()
        orderpoint_obj = self.pool.get('stock.warehouse.orderpoint')
        
        procurement_obj = self.pool.get('procurement.order')
        offset = 0
        ids = [1]
        if automatic:
            self.create_automatic_op(cr, uid, context=context)
        while ids:
            ids = orderpoint_obj.search(cr, uid, [], offset=offset, limit=100)
            for op in orderpoint_obj.browse(cr, uid, ids, context=context):
                prods = self._product_virtual_get(cr, uid, op)
                if prods is None:
                    continue
                if prods < op.product_min_qty:
                    qty = max(op.product_min_qty, op.product_max_qty)-prods

                    reste = qty % op.qty_multiple
                    if reste > 0:
                        qty += op.qty_multiple - reste

                    if qty <= 0:
                        continue
                    if op.product_id.type not in ('consu'):
                        if op.procurement_draft_ids:
                        # Check draft procurement related to this order point
                            pro_ids = [x.id for x in op.procurement_draft_ids]
                            procure_datas = procurement_obj.read(
                                cr, uid, pro_ids, ['id', 'product_qty'], context=context)
                            to_generate = qty
                            for proc_data in procure_datas:
                                if to_generate >= proc_data['product_qty']:
                                    self.signal_button_confirm(cr, uid, [proc_data['id']])
                                    procurement_obj.write(cr, uid, [proc_data['id']],  {'origin': op.name}, context=context)
                                    to_generate -= proc_data['product_qty']
                                if not to_generate:
                                    break
                            qty = to_generate

                    if qty:
                        proc_id = procurement_obj.create(cr, uid,
                                                         self._prepare_orderpoint_procurement(cr, uid, op, qty, context=context),
                                                         context=context)
                        self.check(cr, uid, [proc_id])
                        self.run(cr, uid, [proc_id])
                        orderpoint_obj.write(cr, uid, [op.id],
                                {'procurement_id': proc_id}, context=context)
            offset += len(ids)
            if use_new_cursor:
                cr.commit()
        if use_new_cursor:
            cr.commit()
            cr.close()
        return {}
