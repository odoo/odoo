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

from osv import fields, osv, orm

import tools

class procurement_order(osv.osv):
    _name = "procurement.order"
    _inherit = "procurement.order"
    _columns = {
        'task_id': fields.many2one('project.task', 'Task'),
        'sale_line_id': fields.many2one('sale.order.line', 'Sale order line')
    }
    def check_produce_service(self, cr, uid, procurement, context=None):
        return True

    def action_produce_assign_service(self, cr, uid, ids, context=None):
        for procurement in self.browse(cr, uid, ids, context=context):
            self.write(cr, uid, [procurement.id], {'state': 'running'})
            planned_hours = procurement.product_qty
            task_id = self.pool.get('project.task').create(cr, uid, {
                'name': '%s:%s' % (procurement.origin or '', procurement.product_id.name),
                'date_deadline': procurement.date_planned,
                'planned_hours':planned_hours,
                'remaining_hours': planned_hours,
                'user_id': procurement.product_id.product_manager.id,
                'notes': procurement.note,
                'procurement_id': procurement.id,
                'description': procurement.note,
                'date_deadline': procurement.date_planned,
                'project_id': procurement.product_id.project_id and procurement.product_id.project_id.id or False,
                'state': 'draft',
                'company_id': procurement.company_id.id,
                'sale_id':procurement.sale_line_id.order_id.id
            },context=context)
            self.write(cr, uid, [procurement.id],{'task_id':task_id})
        return task_id
    
procurement_order()

class sale_order(osv.osv):
    _inherit ='sale.order'
       
    def _picked_rate(self, cr, uid, ids, name, arg, context=None):
        temp = {}
        if not ids:
            return {}
        res = super(sale_order, self)._picked_rate(cr, uid, ids, name, arg, context=context)
        cr.execute('''select so.id as sale_id, t.planned_hours, t.state as task_state ,
                    t.id as task_id, ptw.hours as task_hours
                    from project_task as t
                    left join sale_order as so on so.id = t.sale_id  
                    left join project_task_work as ptw on t.id = ptw.task_id
                    where so.id in %s ''',(tuple(ids),))
        r1 = cr.dictfetchall()
        if not r1:
            return res
        test = {}
        for id in ids:
            test[id] = {}
            test[id]['number_of_done'] = 0
            test[id]['number_of_others'] = 0
            test[id]['total_no_task'] = 0
            test[id]['percentage'] = 0.0
            test[id]['number_of_stockable'] = 0.0
            test[id]['number_of_planned'] = 0.0
            test[id]['time_spent'] = 0.0            

        for item in r1:
            flag = False
            flag2 = False
            if not item['task_hours'] and item['task_state'] == 'done': # If Task hours not given and task completed
                flag = True
                
            if item['task_hours'] and item['task_state'] == 'done': #If Task hours but Task in Done state as well as task work != planned hours
                flag2 = True

            if item['task_hours']: # If task work in the task
                test[item['sale_id']]['time_spent'] += item['task_hours']
            
            if item['task_state'] == 'done': # If State is in done state
                test[item['sale_id']]['number_of_done'] += 1
            else: # Else Part
                 test[item['sale_id']]['number_of_others'] += 1
            
            # dict calculated here
            test[item['sale_id']]['number_of_planned'] += item['planned_hours']
            test[item['sale_id']]['total_no_task'] += 1
            test[item['sale_id']]['percentage'] = float(test[item['sale_id']]['time_spent']) / test[item['sale_id']]['number_of_planned'] * 100
            
            
            if flag: # Flag If Task is done without Task hours
                test[item['sale_id']]['percentage'] = (float(test[item['sale_id']]['number_of_done']) / test[item['sale_id']]['number_of_planned']) * 100
            
            if flag2: # Flag 2 Task with work and state is in done state as well as task work != planned hours 
               test[item['sale_id']]['percentage'] = (float(test[item['sale_id']]['number_of_done']) / test[item['sale_id']]['number_of_planned']) * 100

    
        for sale in self.browse(cr,uid,ids,context=None):
            # Non service type products are calculated here 
            test[item['sale_id']]['number_of_stockable'] = len(sale.order_line) - test[item['sale_id']]['total_no_task']
           
            # condition for the percent calculation
            if test[item['sale_id']]['percentage'] == 100 and res[sale.id] == 100:
                continue
            elif test[item['sale_id']]['number_of_stockable'] == 0:
                res[sale.id] = (test[sale.id]['percentage'])
            else:    
                res[sale.id] = (res[sale.id] + test[sale.id]['percentage']) / (test[item['sale_id']]['number_of_stockable'] + test[item['sale_id']]['total_no_task'])
        return res
     
    _columns = {
                    'picked_rate': fields.function(_picked_rate, method=True, string='Picked', type='float'),
               }
  
sale_order()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
