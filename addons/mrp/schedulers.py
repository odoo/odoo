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

from osv import osv
import netsvc
import pooler
from mx import DateTime
import time


class mrp_procurement(osv.osv):
    _inherit = 'mrp.procurement'

    def _procure_confirm(self, cr, uid, ids=None, use_new_cursor=False, context=None):
        '''
        use_new_cursor: False or the dbname
        '''
        if not context:
            context = {}

        if use_new_cursor:
            cr = pooler.get_db(use_new_cursor).cursor()
        wf_service = netsvc.LocalService("workflow")

        procurement_obj = self.pool.get('mrp.procurement')
        if not ids:
            ids = procurement_obj.search(cr, uid, [], order="date_planned")
        for id in ids:
            wf_service.trg_validate(uid, 'mrp.procurement', id, 'button_restart', cr)
        if use_new_cursor:
            cr.commit()

        company = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id
        maxdate = DateTime.now() + DateTime.RelativeDateTime(days=company.schedule_range)
        start_date = time.strftime('%Y-%m-%d, %Hh %Mm %Ss')
        offset = 0
        report = []
        report_total = 0
        report_except = 0
        report_later = 0
        while True:
            cr.execute('select id from mrp_procurement where state=%s and procure_method=%s order by date_planned limit 500 offset %s', ('confirmed', 'make_to_order', offset))
            ids = map(lambda x: x[0], cr.fetchall())
            for proc in procurement_obj.browse(cr, uid, ids):
                if (maxdate.strftime('%Y-%m-%d')>=proc.date_planned):
                    wf_service.trg_validate(uid, 'mrp.procurement', proc.id, 'button_check', cr)
                else:
                    offset += 1
                    report_later += 1
            for proc in procurement_obj.browse(cr, uid, ids):
                if proc.state == 'exception':
                    report.append('PROC %d: on order - %3.2f %-5s - %s' % \
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
            ids = self.pool.get('mrp.procurement').search(cr, uid, [('state', '=', 'confirmed'), ('procure_method', '=', 'make_to_stock')], offset=offset)
            for proc in procurement_obj.browse(cr, uid, ids):
                if ((maxdate).strftime('%Y-%m-%d') >= proc.date_planned) :
                    wf_service.trg_validate(uid, 'mrp.procurement', proc.id, 'button_check', cr)
                    report_ids.append(proc.id)
                else:
                    report_later += 1
                report_total += 1
            for proc in procurement_obj.browse(cr, uid, report_ids):
                if proc.state == 'exception':
                    report.append('PROC %d: from stock - %3.2f %-5s - %s' % \
                            (proc.id, proc.product_qty, proc.product_uom.name,
                                proc.product_id.name,))
                    report_except += 1
            if use_new_cursor:
                cr.commit()
            offset += len(ids)
            if not ids: break
        end_date = time.strftime('%Y-%m-%d, %Hh %Mm %Ss')
        if uid:
            request = self.pool.get('res.request')
            summary = '''Here is the procurement scheduling report.

    Computation Started; %s
    Computation Finished; %s

    Total procurement: %d
    Exception procurement: %d
    Not run now procurement: %d

    Exceptions;
    '''% (start_date, end_date, report_total, report_except, report_later)
            summary += '\n'.join(report)
            request.create(cr, uid,
                {'name': "Procurement calculation report.",
                    'act_from': uid,
                    'act_to': uid,
                    'body': summary,
                })
        if use_new_cursor:
            cr.commit()
            cr.close()
        return {}

    def create_automatic_op(self, cr, uid, context=None):
        if not context:
            context = {}
        product_obj = self.pool.get('product.product')
        proc_obj = self.pool.get('mrp.procurement')
        warehouse_obj = self.pool.get('stock.warehouse')
        wf_service = netsvc.LocalService("workflow")

        warehouse_ids = warehouse_obj.search(cr, uid, [], context=context)

        cr.execute('select id from product_product')
        products_id = [x for x, in cr.fetchall()]

        for warehouse in warehouse_obj.browse(cr, uid, warehouse_ids, context=context):
            context['warehouse'] = warehouse
            for product in self.pool.get('product.product').browse(cr, uid, products_id, context=context):
                if product.virtual_available >= 0.0:
                    continue

                newdate = DateTime.now()
                if product.supply_method == 'buy':
                    location_id = warehouse.lot_input_id.id
                elif product.supply_method == 'produce':
                    location_id = warehouse.lot_stock_id.id
                else:
                    continue
                proc_id = proc_obj.create(cr, uid, {
                    'name': 'Automatic OP: %s' % product.name,
                    'origin': 'SCHEDULER',
                    'date_planned': newdate.strftime('%Y-%m-%d %H:%M:%S'),
                    'product_id': product.id,
                    'product_qty': -product.virtual_available,
                    'product_uom': product.uom_id.id,
                    'location_id': location_id,
                    'procure_method': 'make_to_order',
                    })
                wf_service.trg_validate(uid, 'mrp.procurement', proc_id, 'button_confirm', cr)
                wf_service.trg_validate(uid, 'mrp.procurement', proc_id, 'button_check', cr)

    def _procure_orderpoint_confirm(self, cr, uid, automatic=False,\
            use_new_cursor=False, context=None, user_id=False):
        '''
        use_new_cursor: False or the dbname
        '''
        if not context:
            context = {}
        if use_new_cursor:
            cr = pooler.get_db(use_new_cursor).cursor()
        orderpoint_obj = self.pool.get('stock.warehouse.orderpoint')
        location_obj = self.pool.get('stock.location')
        procurement_obj = self.pool.get('mrp.procurement')
        request_obj = self.pool.get('res.request')
        wf_service = netsvc.LocalService("workflow")
        report = []
        offset = 0
        ids = [1]
        if automatic:
            self.create_automatic_op(cr, uid, context=context)
        while ids:
            ids = orderpoint_obj.search(cr, uid, [
                ('product_id.active', '=', True),
                ('product_id.purchase_ok', '=', True),
            ], offset=offset, limit=100)
            for op in orderpoint_obj.browse(cr, uid, ids):
                if op.procurement_id and op.procurement_id.purchase_id and op.procurement_id.purchase_id.state in ('draft', 'confirmed'):
                    continue
                prods = location_obj._product_virtual_get(cr, uid,
                        op.location_id.id, [op.product_id.id],
                        {'uom': op.product_uom.id})[op.product_id.id]
                if prods < op.product_min_qty:
                    qty = max(op.product_min_qty, op.product_max_qty)-prods
                    reste = qty % op.qty_multiple
                    if reste > 0:
                        qty += op.qty_multiple - reste
                    newdate = DateTime.now() + DateTime.RelativeDateTime(
                            days=int(op.product_id.seller_delay))
                    if op.product_id.supply_method == 'buy':
                        location_id = op.warehouse_id.lot_input_id
                    elif op.product_id.supply_method == 'produce':
                        location_id = op.warehouse_id.lot_stock_id
                    else:
                        continue
                    if qty <= 0:
                        continue
                    if op.product_id.type not in ('consu'):
                        proc_id = procurement_obj.create(cr, uid, {
                            'name': 'OP:' + str(op.id),
                            'date_planned': newdate.strftime('%Y-%m-%d'),
                            'product_id': op.product_id.id,
                            'product_qty': qty,
                            'product_uom': op.product_uom.id,
                            'location_id': op.warehouse_id.lot_input_id.id,
                            'procure_method': 'make_to_order',
                            'origin': op.name
                        })
                        wf_service.trg_validate(uid, 'mrp.procurement', proc_id,
                                'button_confirm', cr)
                        wf_service.trg_validate(uid, 'mrp.procurement', proc_id,
                                'button_check', cr)
                        orderpoint_obj.write(cr, uid, [op.id],
                                {'procurement_id': proc_id})
            offset += len(ids)
            if use_new_cursor:
                cr.commit()
        if user_id and report:
            request_obj.create(cr, uid, {
                'name': 'Orderpoint report.',
                'act_from': user_id,
                'act_to': user_id,
                'body': '\n'.join(report)
                })
        if use_new_cursor:
            cr.commit()
            cr.close()
        return {}
mrp_procurement()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
