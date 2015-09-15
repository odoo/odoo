# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields
from openerp.osv import osv
import time
from datetime import datetime
from openerp.tools.translate import _
from openerp.exceptions import UserError

#----------------------------------------------------------
# Work Centers
#----------------------------------------------------------
# capacity_hour : capacity per hour. default: 1.0.
#          Eg: If 5 concurrent operations at one time: capacity = 5 (because 5 employees)
# unit_per_cycle : how many units are produced for one cycle


class mrp_operations_operation_code(osv.osv):
    _name="mrp_operations.operation.code"
    _columns={
        'name': fields.char('Operation Name', required=True),
        'code': fields.char('Code', size=16, required=True),
        'start_stop': fields.selection([('start','Start'),('pause','Pause'),('resume','Resume'),('cancel','Cancelled'),('done','Done')], 'Status', required=True),
    }

class mrp_operations_operation(osv.osv):
    _name="mrp_operations.operation"

    def _order_date_search_production(self, cr, uid, ids, context=None):
        """ Finds operations for a production order.
        @return: List of ids
        """
        operation_ids = self.pool.get('mrp_operations.operation').search(cr, uid, [('production_id','=',ids[0])], context=context)
        return operation_ids

    def _get_order_date(self, cr, uid, ids, field_name, arg, context=None):
        """ Calculates planned date for an operation.
        @return: Dictionary of values
        """
        res={}
        operation_obj = self.browse(cr, uid, ids, context=context)
        for operation in operation_obj:
                res[operation.id] = operation.production_id.date_planned
        return res

    def calc_delay(self, cr, uid, vals):
        """ Calculates delay of work order.
        @return: Delay
        """
        code_lst = []
        time_lst = []

        code_ids = self.pool.get('mrp_operations.operation.code').search(cr, uid, [('id','=',vals['code_id'])])
        code = self.pool.get('mrp_operations.operation.code').browse(cr, uid, code_ids)[0]

        oper_ids = self.search(cr,uid,[('production_id','=',vals['production_id']),('workcenter_id','=',vals['workcenter_id'])])
        oper_objs = self.browse(cr,uid,oper_ids)

        for oper in oper_objs:
            code_lst.append(oper.code_id.start_stop)
            time_lst.append(oper.date_start)

        code_lst.append(code.start_stop)
        time_lst.append(vals['date_start'])
        diff = 0
        for i in range(0,len(code_lst)):
            if code_lst[i] == 'pause' or code_lst[i] == 'done' or code_lst[i] == 'cancel':
                if not i: continue
                if code_lst[i-1] not in ('resume','start'):
                   continue
                a = datetime.strptime(time_lst[i-1],'%Y-%m-%d %H:%M:%S')
                b = datetime.strptime(time_lst[i],'%Y-%m-%d %H:%M:%S')
                diff += (b-a).days * 24
                diff += (b-a).seconds / float(60*60)
        return diff

    def check_operation(self, cr, uid, vals):
        """ Finds which operation is called ie. start, pause, done, cancel.
        @param vals: Dictionary of values.
        @return: True or False
        """
        code_ids=self.pool.get('mrp_operations.operation.code').search(cr,uid,[('id','=',vals['code_id'])])
        code=self.pool.get('mrp_operations.operation.code').browse(cr,uid,code_ids)[0]
        code_lst = []
        oper_ids=self.search(cr,uid,[('production_id','=',vals['production_id']),('workcenter_id','=',vals['workcenter_id'])])
        oper_objs=self.browse(cr,uid,oper_ids)

        if not oper_objs:
            if code.start_stop!='start':
                raise UserError(_('Operation is not started yet!'))
                return False
        else:
            for oper in oper_objs:
                 code_lst.append(oper.code_id.start_stop)
            if code.start_stop=='start':
                    if 'start' in code_lst:
                        raise UserError(_('Operation has already started! You can either Pause/Finish/Cancel the operation.'))
                        return False
            if code.start_stop=='pause':
                    if  code_lst[len(code_lst)-1]!='resume' and code_lst[len(code_lst)-1]!='start':
                        raise UserError(_('In order to Pause the operation, it must be in the Start or Resume state!'))
                        return False
            if code.start_stop=='resume':
                if code_lst[len(code_lst)-1]!='pause':
                   raise UserError(_('In order to Resume the operation, it must be in the Pause state!'))
                   return False

            if code.start_stop=='done':
               if code_lst[len(code_lst)-1]!='start' and code_lst[len(code_lst)-1]!='resume':
                  raise UserError(_('In order to Finish the operation, it must be in the Start or Resume state!'))
                  return False
               if 'cancel' in code_lst:
                  raise UserError(_('Operation is Already Cancelled!'))
                  return False
            if code.start_stop=='cancel':
               if  not 'start' in code_lst :
                   raise UserError(_('No operation to cancel.'))
                   return False
               if 'done' in code_lst:
                  raise UserError(_('Operation is already finished!'))
                  return False
        return True

    def write(self, cr, uid, ids, vals, context=None):
        oper_objs = self.browse(cr, uid, ids, context=context)[0]
        vals['production_id']=oper_objs.production_id.id
        vals['workcenter_id']=oper_objs.workcenter_id.id

        if 'code_id' in vals:
            self.check_operation(cr, uid, vals)

        if 'date_start' in vals:
            vals['date_start']=vals['date_start']
            vals['code_id']=oper_objs.code_id.id
            delay=self.calc_delay(cr, uid, vals)
            wc_op_id=self.pool.get('mrp.production.workcenter.line').search(cr,uid,[('workcenter_id','=',vals['workcenter_id']),('production_id','=',vals['production_id'])])
            self.pool.get('mrp.production.workcenter.line').write(cr,uid,wc_op_id,{'delay':delay})

        return super(mrp_operations_operation, self).write(cr, uid, ids, vals, context=context)

    def create(self, cr, uid, vals, context=None):
        workcenter_pool = self.pool.get('mrp.production.workcenter.line')
        code_ids=self.pool.get('mrp_operations.operation.code').search(cr,uid,[('id','=',vals['code_id'])])
        code=self.pool.get('mrp_operations.operation.code').browse(cr, uid, code_ids, context=context)[0]
        wc_op_id=workcenter_pool.search(cr,uid,[('workcenter_id','=',vals['workcenter_id']),('production_id','=',vals['production_id'])])
        if code.start_stop in ('start','done','pause','cancel','resume'):
            if not wc_op_id:
                production_obj=self.pool.get('mrp.production').browse(cr, uid, vals['production_id'], context=context)
                wc_op_id.append(workcenter_pool.create(cr,uid,{'production_id':vals['production_id'],'name':production_obj.product_id.name,'workcenter_id':vals['workcenter_id']}))
            if code.start_stop=='start':
                workcenter_pool.action_start_working(cr,uid,wc_op_id)
                workcenter_pool.signal_workflow(cr, uid, [wc_op_id[0]], 'button_start_working')

            if code.start_stop=='done':
                workcenter_pool.action_done(cr,uid,wc_op_id)
                workcenter_pool.signal_workflow(cr, uid, [wc_op_id[0]], 'button_done')
                self.pool.get('mrp.production').write(cr,uid,vals['production_id'],{'date_finished':datetime.now().strftime('%Y-%m-%d %H:%M:%S')})

            if code.start_stop=='pause':
                workcenter_pool.action_pause(cr,uid,wc_op_id)
                workcenter_pool.signal_workflow(cr, uid, [wc_op_id[0]], 'button_pause')

            if code.start_stop=='resume':
                workcenter_pool.action_resume(cr,uid,wc_op_id)
                workcenter_pool.signal_workflow(cr, uid, [wc_op_id[0]], 'button_resume')

            if code.start_stop=='cancel':
                workcenter_pool.action_cancel(cr,uid,wc_op_id)
                workcenter_pool.signal_workflow(cr, uid, [wc_op_id[0]], 'button_cancel')

        if not self.check_operation(cr, uid, vals):
            return
        delay=self.calc_delay(cr, uid, vals)
        line_vals = {}
        line_vals['delay'] = delay
        if vals.get('date_start',False):
            if code.start_stop == 'done':
                line_vals['date_finished'] = vals['date_start']
            elif code.start_stop == 'start':
                line_vals['date_start'] = vals['date_start']

        self.pool.get('mrp.production.workcenter.line').write(cr, uid, wc_op_id, line_vals, context=context)

        return super(mrp_operations_operation, self).create(cr, uid, vals, context=context)

    def initialize_workflow_instance(self, cr, uid, context=None):
        mrp_production_workcenter_line = self.pool.get('mrp.production.workcenter.line')
        line_ids = mrp_production_workcenter_line.search(cr, uid, [], context=context)
        mrp_production_workcenter_line.create_workflow(cr, uid, line_ids)
        return True

    _columns={
        'production_id':fields.many2one('mrp.production','Production',required=True),
        'workcenter_id':fields.many2one('mrp.workcenter','Work Center',required=True),
        'code_id':fields.many2one('mrp_operations.operation.code','Code',required=True),
        'date_start': fields.datetime('Start Date'),
        'date_finished': fields.datetime('End Date'),
        'order_date': fields.function(_get_order_date,string='Order Date',type='date',store={'mrp.production':(_order_date_search_production,['date_planned'], 10)}),
        }
    _defaults={
        'date_start': lambda *a:datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
