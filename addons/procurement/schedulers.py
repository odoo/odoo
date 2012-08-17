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
import netsvc
import pooler
from osv import osv
from osv import fields
from tools.translate import _
from tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
import tools

class procurement_order(osv.osv):
    _inherit = 'procurement.order'

    def run_scheduler(self, cr, uid, automatic=False, use_new_cursor=False, context=None):
        ''' Runs through scheduler.
        @param use_new_cursor: False or the dbname
        '''
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
            start_date = fields.datetime.now()
            offset = 0
            report = []
            report_total = 0
            report_except = 0
            report_later = 0
            while True:
                ids = procurement_obj.search(cr, uid, [('state', '=', 'confirmed'), ('procure_method', '=', 'make_to_order')], offset=offset, limit=500, order='priority, date_planned', context=context)
                for proc in procurement_obj.browse(cr, uid, ids, context=context):
                    if maxdate >= proc.date_planned:
                        wf_service.trg_validate(uid, 'procurement.order', proc.id, 'button_check', cr)
                    else:
                        offset += 1
                        report_later += 1

                    if proc.state == 'exception':
                        report.append(_('PROC %d: on order - %3.2f %-5s - %s') % \
                                (proc.id, proc.product_qty, proc.product_uom.name,
                                    proc.product_id.name))
                        report_except += 1
                    report_total += 1
                if use_new_cursor:
                    cr.commit()
                if not ids:
                    break
            offset = 0
            ids = []
            while True:
                report_ids = []
                ids = procurement_obj.search(cr, uid, [('state', '=', 'confirmed'), ('procure_method', '=', 'make_to_stock')], offset=offset)
                for proc in procurement_obj.browse(cr, uid, ids):
                    if maxdate >= proc.date_planned:
                        wf_service.trg_validate(uid, 'procurement.order', proc.id, 'button_check', cr)
                        report_ids.append(proc.id)
                    else:
                        report_later += 1
                    report_total += 1

                    if proc.state == 'exception':
                        report.append(_('PROC %d: from stock - %3.2f %-5s - %s') % \
                                (proc.id, proc.product_qty, proc.product_uom.name,
                                    proc.product_id.name,))
                        report_except += 1


                if use_new_cursor:
                    cr.commit()
                offset += len(ids)
                if not ids: break
            end_date = fields.datetime.now()
            if uid:
                # Chatter: old res.request is now a chatter on res.users, id=uid
                summary = _("""Here is the procurement scheduling report.

        Start Time: %s 
        End Time: %s 
        Total Procurements processed: %d 
        Procurements with exceptions: %d 
        Skipped Procurements (scheduled date outside of scheduler range) %d 

        Exceptions:\n""") % (start_date, end_date, report_total, report_except, report_later)
                summary += '\n'.join(report)
                procurement_obj.message_post(cr, uid, ids, body=summary, context=context)

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
        products_ids = product_obj.search(cr, uid, [('purchase_ok', '=', True)], order='id', context=context)

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
        location_obj = self.pool.get('stock.location')
        procurement_obj = self.pool.get('procurement.order')
        wf_service = netsvc.LocalService("workflow")
        offset = 0
        ids = [1]
        if automatic:
            self.create_automatic_op(cr, uid, context=context)
        while ids:
            ids = orderpoint_obj.search(cr, uid, [], offset=offset, limit=100)
            for op in orderpoint_obj.browse(cr, uid, ids, context=context):
                if op.procurement_id.state != 'exception':
                    if op.procurement_id and hasattr(op.procurement_id, 'purchase_id'):
                        if op.procurement_id.purchase_id.state in ('draft', 'confirmed'):
                            continue
                prods = location_obj._product_virtual_get(cr, uid,
                        op.location_id.id, [op.product_id.id],
                        {'uom': op.product_uom.id})[op.product_id.id]

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
            offset += len(ids)
            if use_new_cursor:
                cr.commit()
        if use_new_cursor:
            cr.commit()
            cr.close()
        return {}

procurement_order()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
