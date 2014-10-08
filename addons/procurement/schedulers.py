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

from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp import netsvc
from openerp import pooler
from openerp.osv import osv
from openerp.osv import fields
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from openerp import tools
from psycopg2 import OperationalError

class procurement_order(osv.osv):
    _inherit = 'procurement.order'

    def run_scheduler(self, cr, uid, automatic=False, use_new_cursor=False, context=None):
        ''' Runs through scheduler.
        @param use_new_cursor: False or the dbname
        '''
        if use_new_cursor:
            use_new_cursor = cr.dbname
        self._procure_confirm(cr, uid, use_new_cursor=use_new_cursor, context=context)
        self._procure_orderpoint_confirm(cr, uid, automatic=automatic,\
                use_new_cursor=use_new_cursor, context=context)

    def _procure_confirm(self, cr, uid, ids=None, use_new_cursor=False, context=None):
        '''
        Call the scheduler to check the procurement order

        @param self: The object pointer
        @param cr: The current row, from the database cursor,
        @param uid: The current user ID for security checks
        @param ids: List of selected IDs
        @param use_new_cursor: False or the dbname
        @param context: A standard dictionary for contextual values
        @return:  Dictionary of values
        '''
        if context is None:
            context = {}
        try:
            if use_new_cursor:
                cr = pooler.get_db(use_new_cursor).cursor()
            wf_service = netsvc.LocalService("workflow")

            procurement_obj = self.pool.get('procurement.order')
            if not ids:
                ids = procurement_obj.search(cr, uid, [('state', '=', 'exception')], order="date_planned")
            for id in ids:
                wf_service.trg_validate(uid, 'procurement.order', id, 'button_restart', cr)
            if use_new_cursor:
                cr.commit()
            company = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id
            maxdate = (datetime.today() + relativedelta(days=company.schedule_range)).strftime(tools.DEFAULT_SERVER_DATE_FORMAT)
            prev_ids = []
            while True:
                ids = procurement_obj.search(cr, uid, [('state', '=', 'confirmed'), ('procure_method', '=', 'make_to_order'), ('date_planned', '<', maxdate)], limit=500, order='priority, date_planned', context=context)
                for proc in procurement_obj.browse(cr, uid, ids, context=context):
                    try:
                        wf_service.trg_validate(uid, 'procurement.order', proc.id, 'button_check', cr)

                        if use_new_cursor:
                            cr.commit()
                    except OperationalError:
                        if use_new_cursor:
                            cr.rollback()
                            continue
                        else:
                            raise
                if not ids or prev_ids == ids:
                    break
                else:
                    prev_ids = ids
            ids = []
            prev_ids = []
            while True:
                ids = procurement_obj.search(cr, uid, [('state', '=', 'confirmed'), ('procure_method', '=', 'make_to_stock'), ('date_planned', '<', maxdate)], limit=500)
                for proc in procurement_obj.browse(cr, uid, ids):
                    try:
                        wf_service.trg_validate(uid, 'procurement.order', proc.id, 'button_check', cr)

                        if use_new_cursor:
                            cr.commit()
                    except OperationalError:
                        if use_new_cursor:
                            cr.rollback()
                            continue
                        else:
                            raise
                if not ids or prev_ids == ids:
                    break
                else:
                    prev_ids = ids

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
                'procure_method': 'make_to_order',}

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
        wf_service = netsvc.LocalService("workflow")

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
                    location_id = warehouse.lot_input_id.id
                elif product.supply_method == 'produce':
                    location_id = warehouse.lot_stock_id.id
                else:
                    continue
                proc_id = proc_obj.create(cr, uid,
                            self._prepare_automatic_op_procurement(cr, uid, product, warehouse, location_id, context=context),
                            context=context)
                wf_service.trg_validate(uid, 'procurement.order', proc_id, 'button_confirm', cr)
                wf_service.trg_validate(uid, 'procurement.order', proc_id, 'button_check', cr)
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
                'procure_method': 'make_to_order',
                'origin': orderpoint.name}
        
    def _product_virtual_get(self, cr, uid, order_point):
        location_obj = self.pool.get('stock.location')
        return location_obj._product_virtual_get(cr, uid,
                order_point.location_id.id, [order_point.product_id.id],
                {'uom': order_point.product_uom.id})[order_point.product_id.id]

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
            cr = pooler.get_db(use_new_cursor).cursor()
        orderpoint_obj = self.pool.get('stock.warehouse.orderpoint')
        
        procurement_obj = self.pool.get('procurement.order')
        wf_service = netsvc.LocalService("workflow")
        ids = [1]
        prev_ids = []
        if automatic:
            self.create_automatic_op(cr, uid, context=context)
        orderpoint_ids = orderpoint_obj.search(cr, uid, [])
        while orderpoint_ids:
            ids = orderpoint_ids[:100]
            del orderpoint_ids[:100]
            for op in orderpoint_obj.browse(cr, uid, ids, context=context):
                try:
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
                                        wf_service.trg_validate(uid, 'procurement.order', proc_data['id'], 'button_confirm', cr)
                                        procurement_obj.write(cr, uid, [proc_data['id']],  {'origin': op.name}, context=context)
                                        to_generate -= proc_data['product_qty']
                                    if not to_generate:
                                        break
                                qty = to_generate

                        if qty:
                            proc_id = procurement_obj.create(cr, uid,
                                                             self._prepare_orderpoint_procurement(cr, uid, op, qty, context=context),
                                                             context=context)
                            wf_service.trg_validate(uid, 'procurement.order', proc_id,
                                    'button_confirm', cr)
                            wf_service.trg_validate(uid, 'procurement.order', proc_id,
                                    'button_check', cr)
                            orderpoint_obj.write(cr, uid, [op.id],
                                    {'procurement_id': proc_id}, context=context)
                    if use_new_cursor:
                        cr.commit()
                except OperationalError:
                    if use_new_cursor:
                        orderpoint_ids.append(op.id)
                        cr.rollback()
                        continue
                    else:
                        raise
            if prev_ids == ids:
                break
            else:
                prev_ids = ids

        if use_new_cursor:
            cr.commit()
            cr.close()
        return {}

procurement_order()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
