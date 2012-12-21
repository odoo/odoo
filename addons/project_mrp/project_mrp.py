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
from openerp import netsvc

class project_task(osv.osv):
    _name = "project.task"
    _inherit = "project.task"
    _columns = {
        'procurement_id': fields.many2one('procurement.order', 'Procurement', ondelete='set null'),
        'sale_line_id': fields.related('procurement_id', 'sale_line_id', type='many2one', relation='sale.order.line', store=True, string='Sales Order Line'),
    }

    def _validate_subflows(self, cr, uid, ids):
        wf_service = netsvc.LocalService("workflow")
        for task in self.browse(cr, uid, ids):
            if task.procurement_id:
                wf_service.trg_write(uid, 'procurement.order', task.procurement_id.id, cr)

    def do_close(self, cr, uid, ids, *args, **kwargs):
        res = super(project_task, self).do_close(cr, uid, ids, *args, **kwargs)
        self._validate_subflows(cr, uid, ids)
        return res

    def do_cancel(self, cr, uid, ids, *args, **kwargs):
        res = super(project_task, self).do_cancel(cr, uid, ids, *args, **kwargs)
        self._validate_subflows(cr, uid, ids)
        return res
project_task()

class product_product(osv.osv):
    _inherit = "product.product"
    _columns = {
        'project_id': fields.many2one('project.project', 'Project', ondelete='set null',)
    }
product_product()

class sale_order(osv.osv):
    _inherit ='sale.order'

    def _prepare_order_line_procurement(self, cr, uid, order, line, move_id, date_planned, context=None):
        proc_data = super(sale_order, self)._prepare_order_line_procurement(cr,
                uid, order, line, move_id, date_planned, context=context)
        proc_data['sale_line_id'] = line.id
        return proc_data

    def _picked_rate(self, cr, uid, ids, name, arg, context=None):
        if not ids:
            return {}
        res_sale = {}
        res = super(sale_order, self)._picked_rate(cr, uid, ids, name, arg, context=context)
        cr.execute('''select sol.order_id as sale_id, t.state as task_state ,
                    t.id as task_id, sum(sol.product_uom_qty) as total
                    from project_task as t
                    left join sale_order_line as sol on sol.id = t.sale_line_id
                    where sol.order_id in %s group by sol.order_id,t.state,t.id ''',(tuple(ids),))
        sale_task_data = cr.dictfetchall()

        if not sale_task_data:
            return res

        for id in ids:
            res_sale[id] = {
                'number_of_done': 0,
                'total_no_task': 0,
            }
        #compute the sum of quantity for each SO
        cr.execute('''select sol.order_id as sale_id, sum(sol.product_uom_qty) as total
                    from sale_order_line sol where sol.order_id in %s group by sol.order_id''',(tuple(ids),))
        total_qtty_ref = cr.dictfetchall()
        for item in total_qtty_ref:
            res_sale[item['sale_id']]['number_of_stockable'] = item['total']

        for item in sale_task_data:
            res_sale[item['sale_id']]['total_no_task'] += item['total']
            if item['task_state'] == 'done':
                res_sale[item['sale_id']]['number_of_done'] += item['total']

        for sale in self.browse(cr, uid, ids, context=context):
            if 'number_of_stockable' in res_sale[sale.id]:
                res_sale[sale.id]['number_of_stockable'] -= res_sale[sale.id]['total_no_task']
                #adjust previously percentage because now we must also count the product of type service
                res[sale.id] = res[sale.id] * float(res_sale[sale.id]['number_of_stockable']) / (res_sale[sale.id]['number_of_stockable'] + res_sale[sale.id]['total_no_task'])
                #add the task
                res[sale.id] += res_sale[sale.id]['number_of_done'] * 100 /  (res_sale[sale.id]['number_of_stockable'] + res_sale[sale.id]['total_no_task'])
        return res

    _columns = {
        'picked_rate': fields.function(_picked_rate, method=True, string='Picked', type='float'),
    }

sale_order()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
