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

from osv import fields
from osv import osv
import netsvc
import time
from datetime import datetime
from tools.translate import _

#----------------------------------------------------------
# Work Centers
#----------------------------------------------------------
# capacity_hour : capacity per hour. default: 1.0.
#          Eg: If 5 concurrent operations at one time: capacity = 5 (because 5 employees)
# unit_per_cycle : how many units are produced for one cycle

class stock_move(osv.osv):
    _inherit = 'stock.move'
    _columns = {
        'move_dest_id_lines': fields.one2many('stock.move','move_dest_id', 'Children Moves')
    }

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default.update({
            'move_dest_id_lines': [],
        })
        return super(stock_move, self).copy(cr, uid, id, default, context)

stock_move()

class mrp_production_workcenter_line(osv.osv):
    def _get_date_date(self, cr, uid, ids, field_name, arg, context=None):
        """ Finds starting date.
        @return: Dictionary of values.
        """
        res={}
        for op in self.browse(cr, uid, ids, context=context):
            if op.date_start:
                res[op.id] = op.date_start[:10]
            else:
                res[op.id]=False
        return res

    def _get_date_end(self, cr, uid, ids, field_name, arg, context=None):
        """ Finds ending date.
        @return: Dictionary of values.
        """
        ops = self.browse(cr, uid, ids, context=context)
        date_and_hours_by_cal = [(op.date_planned, op.hour, op.workcenter_id.calendar_id.id) for op in ops if op.date_planned]

        intervals = self.pool.get('resource.calendar').interval_get_multi(cr, uid, date_and_hours_by_cal)

        res = {}
        for op in ops:
            res[op.id] = False
            if op.date_planned:
                i = intervals.get((op.date_planned, op.hour, op.workcenter_id.calendar_id.id))
                if i:
                    res[op.id] = i[-1][1].strftime('%Y-%m-%d %H:%M:%S')
                else:
                    res[op.id] = op.date_planned
        return res

    _inherit = 'mrp.production.workcenter.line'
    _order = "sequence, date_planned"

    _columns = {
       'state': fields.selection([('draft','Draft'),('startworking', 'In Progress'),('pause','Pause'),('cancel','Cancelled'),('done','Finished')],'State', readonly=True,
                                 help="* When a work order is created it is set in 'Draft' state.\n" \
                                       "* When user sets work order in start mode that time it will be set in 'In Progress' state.\n" \
                                       "* When work order is in running mode, during that time if user wants to stop or to make changes in order then can set in 'Pause' state.\n" \
                                       "* When the user cancels the work order it will be set in 'Canceled' state.\n" \
                                       "* When order is completely processed that time it is set in 'Finished' state."),
       'date_start_date': fields.function(_get_date_date, method=True, string='Start Date', type='date'),
       'date_planned': fields.datetime('Scheduled Date'),
       'date_planned_end': fields.function(_get_date_end, method=True, string='End Date', type='datetime'),
       'date_start': fields.datetime('Start Date'),
       'date_finished': fields.datetime('End Date'),
       'delay': fields.float('Working Hours',help="This is lead time between operation start and stop in this Work Center",readonly=True),
       'production_state':fields.related('production_id','state',
            type='selection',
            selection=[('draft','Draft'),('picking_except', 'Picking Exception'),('confirmed','Waiting Goods'),('ready','Ready to Produce'),('in_production','In Production'),('cancel','Canceled'),('done','Done')],
            string='Production State', readonly=True),
       'product':fields.related('production_id','product_id',type='many2one',relation='product.product',string='Product',
            readonly=True),
       'qty':fields.related('production_id','product_qty',type='float',string='Qty',readonly=True, store=True),
       'uom':fields.related('production_id','product_uom',type='many2one',relation='product.uom',string='UOM',readonly=True),
    }

    _defaults = {
        'state': lambda *a: 'draft',
        'delay': lambda *a: 0.0
    }

    def modify_production_order_state(self, cr, uid, ids, action):
        """ Modifies production order state if work order state is changed.
        @param action: Action to perform.
        @return: Nothing
        """
        wf_service = netsvc.LocalService("workflow")
        prod_obj_pool = self.pool.get('mrp.production')
        oper_obj = self.browse(cr, uid, ids)[0]
        prod_obj = oper_obj.production_id
        if action == 'start':
               if prod_obj.state =='confirmed':
                   prod_obj_pool.force_production(cr, uid, [prod_obj.id])
                   wf_service.trg_validate(uid, 'mrp.production', prod_obj.id, 'button_produce', cr)
               elif prod_obj.state =='ready':
                   wf_service.trg_validate(uid, 'mrp.production', prod_obj.id, 'button_produce', cr)
               elif prod_obj.state =='in_production':
                   return
               else:
                   raise osv.except_osv(_('Error!'),_('Production Order Cannot start in [%s] state') % (prod_obj.state,))
        else:
            oper_ids = self.search(cr,uid,[('production_id','=',prod_obj.id)])
            obj = self.browse(cr,uid,oper_ids)
            flag = True
            for line in obj:
                if line.state != 'done':
                     flag = False
            if flag:
                for production in prod_obj_pool.browse(cr, uid, [prod_obj.id], context= None):
                    if production.move_lines or production.move_created_ids:
                        prod_obj_pool.action_produce(cr,uid, production.id, production.product_qty, 'consume_produce', context = None)
                wf_service.trg_validate(uid, 'mrp.production', oper_obj.production_id.id, 'button_produce_done', cr)
        return

    def write(self, cr, uid, ids, vals, context=None, update=True):
        result = super(mrp_production_workcenter_line, self).write(cr, uid, ids, vals, context=context)
        prod_obj = self.pool.get('mrp.production')
        if vals.get('date_planned', False) and update:
            for prod in self.browse(cr, uid, ids, context=context):
                if prod.production_id.workcenter_lines:
                    dstart = min(vals['date_planned'], prod.production_id.workcenter_lines[0]['date_planned'])
                    prod_obj.write(cr, uid, [prod.production_id.id], {'date_start':dstart}, context=context, mini=False)
        return result

    def action_draft(self, cr, uid, ids):
        """ Sets state to draft.
        @return: True
        """
        self.write(cr, uid, ids, {'state':'draft'})
        return True

    def action_start_working(self, cr, uid, ids):
        """ Sets state to start working and writes starting date.
        @return: True
        """
        self.modify_production_order_state(cr, uid, ids, 'start')
        self.write(cr, uid, ids, {'state':'startworking', 'date_start': time.strftime('%Y-%m-%d %H:%M:%S')})
        return True

    def action_done(self, cr, uid, ids):
        """ Sets state to done, writes finish date and calculates delay.
        @return: True
        """
        delay = 0.0
        date_now = time.strftime('%Y-%m-%d %H:%M:%S')
        obj_line = self.browse(cr, uid, ids[0])

        date_start = datetime.strptime(obj_line.date_start,'%Y-%m-%d %H:%M:%S')
        date_finished = datetime.strptime(date_now,'%Y-%m-%d %H:%M:%S')
        delay += (date_finished-date_start).days * 24
        delay += (date_finished-date_start).seconds / float(60*60)

        self.write(cr, uid, ids, {'state':'done', 'date_finished': date_now,'delay':delay})
        self.modify_production_order_state(cr,uid,ids,'done')
        return True

    def action_cancel(self, cr, uid, ids):
        """ Sets state to cancel.
        @return: True
        """
        self.write(cr, uid, ids, {'state':'cancel'})
        return True

    def action_pause(self, cr, uid, ids):
        """ Sets state to pause.
        @return: True
        """
        self.write(cr, uid, ids, {'state':'pause'})
        return True

    def action_resume(self, cr, uid, ids):
        """ Sets state to startworking.
        @return: True
        """
        self.write(cr, uid, ids, {'state':'startworking'})
        return True

mrp_production_workcenter_line()

class mrp_production(osv.osv):
    _inherit = 'mrp.production'
    _columns = {
        'allow_reorder': fields.boolean('Free Serialisation', help="Check this to be able to move independently all production orders, without moving dependent ones."),
    }

    def _production_date_end(self, cr, uid, ids, prop, unknow_none, context=None):
        """ Calculates planned end date of production order.
        @return: Dictionary of values
        """
        result = {}
        for prod in self.browse(cr, uid, ids, context=context):
            result[prod.id] = prod.date_planned
            for line in prod.workcenter_lines:
                result[prod.id] = max(line.date_planned_end, result[prod.id])
        return result

    def action_production_end(self, cr, uid, ids):
        """ Finishes work order if production order is done.
        @return: Super method
        """
        work_obj = self.pool.get('mrp.production.workcenter.line')
        obj = self.browse(cr, uid, ids)[0]
        wf_service = netsvc.LocalService("workflow")
        for workcenter_line in obj.workcenter_lines:
            wf_service.trg_validate(uid, 'mrp.production.workcenter.line', workcenter_line.id, 'button_done', cr)
            if workcenter_line.state == 'draft':
                work_obj.write(cr, uid, workcenter_line.id, {'state': 'done'})
        return super(mrp_production,self).action_production_end(cr, uid, ids)

    def action_in_production(self, cr, uid, ids):
        """ Changes state to In Production and writes starting date.
        @return: True
        """
        obj = self.browse(cr, uid, ids)[0]
        workcenter_pool = self.pool.get('mrp.production.workcenter.line')
        wf_service = netsvc.LocalService("workflow")
        for prod in self.browse(cr, uid, ids):
            workorder_ids = workcenter_pool.search(cr, uid, [('production_id', '=', prod.id)], limit=1)
            for wo_id in workorder_ids:
                wf_service.trg_validate(uid, 'mrp.production.workcenter.line', wo_id, 'button_start_working', cr)
        return super(mrp_production,self).action_in_production(cr, uid, ids)
    
    def action_cancel(self, cr, uid, ids, context=None):
        """ Cancels work order if production order is canceled.
        @return: Super method
        """
        if context is None:
            context = {}
        obj = self.browse(cr, uid, ids)[0]
        wf_service = netsvc.LocalService("workflow")
        for workcenter_line in obj.workcenter_lines:
            wf_service.trg_validate(uid, 'mrp.production.workcenter.line', workcenter_line.id, 'button_cancel', cr)
        return super(mrp_production,self).action_cancel(cr,uid,ids)

    def _compute_planned_workcenter(self, cr, uid, ids, context=None, mini=False):
        """ Computes planned and finished dates for work order.
        @return: Calculated date
        """
        dt_end = datetime.now()
        if context is None:
            context = {}
        for po in self.browse(cr, uid, ids, context=context):
            dt_end = datetime.strptime(po.date_planned, '%Y-%m-%d %H:%M:%S')
            if not po.date_start:
                self.write(cr, uid, [po.id], {
                    'date_start': po.date_planned
                }, context=context, update=False)
            old = None
            for wci in range(len(po.workcenter_lines)):
                wc  = po.workcenter_lines[wci]
                if (old is None) or (wc.sequence>old):
                    dt = dt_end
                if context.get('__last_update'):
                    del context['__last_update']
                if (wc.date_planned < dt.strftime('%Y-%m-%d %H:%M:%S')) or mini:
                    self.pool.get('mrp.production.workcenter.line').write(cr, uid, [wc.id],  {
                        'date_planned': dt.strftime('%Y-%m-%d %H:%M:%S')
                    }, context=context, update=False)
                    i = self.pool.get('resource.calendar').interval_get(
                        cr,
                        uid,
                        wc.workcenter_id.calendar_id and wc.workcenter_id.calendar_id.id or False,
                        dt,
                        wc.hour or 0.0
                    )
                    if i:
                        dt_end = max(dt_end, i[-1][1])
                else:
                    dt_end = datetime.strptime(wc.date_planned_end, '%Y-%m-%d %H:%M:%S')

                old = wc.sequence or 0
            super(mrp_production, self).write(cr, uid, [po.id], {
                'date_finished': dt_end
            })
        return dt_end

    def _move_pass(self, cr, uid, ids, context=None):
        """ Calculates start date for stock moves finding interval from resource calendar.
        @return: True
        """
        for po in self.browse(cr, uid, ids, context=context):
            if po.allow_reorder:
                continue
            todo = po.move_lines
            dt = datetime.strptime(po.date_start,'%Y-%m-%d %H:%M:%S')
            while todo:
                l = todo.pop(0)
                if l.state in ('done','cancel','draft'):
                    continue
                todo += l.move_dest_id_lines
                if l.production_id and (l.production_id.date_finished > dt):
                    if l.production_id.state not in ('done','cancel'):
                        for wc in l.production_id.workcenter_lines:
                            i = self.pool.get('resource.calendar').interval_min_get(
                                cr,
                                uid,
                                wc.workcenter_id.calendar_id.id or False,
                                dt, wc.hour or 0.0
                            )
                            dt = i[0][0]
                        if l.production_id.date_start > dt.strftime('%Y-%m-%d %H:%M:%S'):
                            self.write(cr, uid, [l.production_id.id], {'date_start':dt.strftime('%Y-%m-%d %H:%M:%S')}, mini=True)
        return True

    def _move_futur(self, cr, uid, ids, context=None):
        """ Calculates start date for stock moves.
        @return: True
        """
        for po in self.browse(cr, uid, ids, context=context):
            if po.allow_reorder:
                continue
            for line in po.move_created_ids:
                l = line
                while l.move_dest_id:
                    l = l.move_dest_id
                    if l.state in ('done','cancel','draft'):
                        break
                    if l.production_id.state in ('done','cancel'):
                        break
                    if l.production_id and (l.production_id.date_start < po.date_finished):
                        self.write(cr, uid, [l.production_id.id], {'date_start': po.date_finished})
                        break


    def write(self, cr, uid, ids, vals, context=None, update=True, mini=True):
        direction = {}
        if vals.get('date_start', False):
            for po in self.browse(cr, uid, ids, context=context):
                direction[po.id] = cmp(po.date_start, vals.get('date_start', False))
        result = super(mrp_production, self).write(cr, uid, ids, vals, context=context)
        if (vals.get('workcenter_lines', False) or vals.get('date_start', False)) and update:
            self._compute_planned_workcenter(cr, uid, ids, context=context, mini=mini)
        for d in direction:
            if direction[d] == 1:
                # the production order has been moved to the passed
                self._move_pass(cr, uid, [d], context=context)
                pass
            elif direction[d] == -1:
                self._move_futur(cr, uid, [d], context=context)
                # the production order has been moved to the future
                pass
        return result

    def action_compute(self, cr, uid, ids, properties=[]):
        """ Computes bills of material of a product and planned date of work order.
        @param properties: List containing dictionaries of properties.
        @return: No. of products.
        """
        result = super(mrp_production, self).action_compute(cr, uid, ids, properties=properties)
        self._compute_planned_workcenter(cr, uid, ids, context={})
        return result

mrp_production()

class mrp_operations_operation_code(osv.osv):
    _name="mrp_operations.operation.code"
    _columns={
        'name': fields.char('Operation Name',size=64, required=True),
        'code': fields.char('Code', size=16, required=True),
        'start_stop': fields.selection([('start','Start'),('pause','Pause'),('resume','Resume'),('cancel','Cancelled'),('done','Done')], 'Status', required=True),
    }
mrp_operations_operation_code()

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
                raise osv.except_osv(_('Sorry!'),_('Operation is not started yet !'))
                return False
        else:
            for oper in oper_objs:
                 code_lst.append(oper.code_id.start_stop)
            if code.start_stop=='start':
                    if 'start' in code_lst:
                        raise osv.except_osv(_('Sorry!'),_('Operation has already started !' 'You  can either Pause /Finish/Cancel the operation'))
                        return False
            if code.start_stop=='pause':
                    if  code_lst[len(code_lst)-1]!='resume' and code_lst[len(code_lst)-1]!='start':
                        raise osv.except_osv(_('Error!'),_('You cannot Pause the Operation other then Start/Resume state !'))
                        return False
            if code.start_stop=='resume':
                if code_lst[len(code_lst)-1]!='pause':
                   raise osv.except_osv(_('Error!'),_(' You cannot Resume the operation other then Pause state !'))
                   return False

            if code.start_stop=='done':
               if code_lst[len(code_lst)-1]!='start' and code_lst[len(code_lst)-1]!='resume':
                  raise osv.except_osv(_('Sorry!'),_('You cannot finish the operation without Starting/Resuming it !'))
                  return False
               if 'cancel' in code_lst:
                  raise osv.except_osv(_('Sorry!'),_('Operation is Already Cancelled  !'))
                  return False
            if code.start_stop=='cancel':
               if  not 'start' in code_lst :
                   raise osv.except_osv(_('Error!'),_('There is no Operation to be cancelled !'))
                   return False
               if 'done' in code_lst:
                  raise osv.except_osv(_('Error!'),_('Operation is already finished !'))
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
        wf_service = netsvc.LocalService('workflow')
        code_ids=self.pool.get('mrp_operations.operation.code').search(cr,uid,[('id','=',vals['code_id'])])
        code=self.pool.get('mrp_operations.operation.code').browse(cr, uid, code_ids, context=context)[0]
        wc_op_id=self.pool.get('mrp.production.workcenter.line').search(cr,uid,[('workcenter_id','=',vals['workcenter_id']),('production_id','=',vals['production_id'])])
        if code.start_stop in ('start','done','pause','cancel','resume'):
            if not wc_op_id:
                production_obj=self.pool.get('mrp.production').browse(cr, uid, vals['production_id'], context=context)
                wc_op_id.append(self.pool.get('mrp.production.workcenter.line').create(cr,uid,{'production_id':vals['production_id'],'name':production_obj.product_id.name,'workcenter_id':vals['workcenter_id']}))
            if code.start_stop=='start':
                self.pool.get('mrp.production.workcenter.line').action_start_working(cr,uid,wc_op_id)
                wf_service.trg_validate(uid, 'mrp.production.workcenter.line', wc_op_id[0], 'button_start_working', cr)


            if code.start_stop=='done':
                self.pool.get('mrp.production.workcenter.line').action_done(cr,uid,wc_op_id)
                wf_service.trg_validate(uid, 'mrp.production.workcenter.line', wc_op_id[0], 'button_done', cr)
                self.pool.get('mrp.production').write(cr,uid,vals['production_id'],{'date_finished':datetime.now().strftime('%Y-%m-%d %H:%M:%S')})

            if code.start_stop=='pause':
                self.pool.get('mrp.production.workcenter.line').action_pause(cr,uid,wc_op_id)
                wf_service.trg_validate(uid, 'mrp.production.workcenter.line', wc_op_id[0], 'button_pause', cr)

            if code.start_stop=='resume':
                self.pool.get('mrp.production.workcenter.line').action_resume(cr,uid,wc_op_id)
                wf_service.trg_validate(uid, 'mrp.production.workcenter.line', wc_op_id[0], 'button_resume', cr)

            if code.start_stop=='cancel':
                self.pool.get('mrp.production.workcenter.line').action_cancel(cr,uid,wc_op_id)
                wf_service.trg_validate(uid, 'mrp.production.workcenter.line', wc_op_id[0], 'button_cancel', cr)

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

    _columns={
        'production_id':fields.many2one('mrp.production','Production',required=True),
        'workcenter_id':fields.many2one('mrp.workcenter','Work Center',required=True),
        'code_id':fields.many2one('mrp_operations.operation.code','Code',required=True),
        'date_start': fields.datetime('Start Date'),
        'date_finished': fields.datetime('End Date'),
        'order_date': fields.function(_get_order_date,method=True,string='Order Date',type='date',store={'mrp.production':(_order_date_search_production,['date_planned'], 10)}),
        }
    _defaults={
        'date_start': lambda *a:datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

mrp_operations_operation()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

