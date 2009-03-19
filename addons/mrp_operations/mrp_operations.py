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

from osv import fields
from osv import osv
import ir
import datetime
import netsvc
import time
from mx import DateTime
from tools.translate import _

#----------------------------------------------------------
# Workcenters
#----------------------------------------------------------
# capacity_hour : capacity per hour. default: 1.0.
#          Eg: If 5 concurrent operations at one time: capacity = 5 (because 5 employees)
# unit_per_cycle : how many units are produced for one cycle
#
# TODO: Work Center may be recursive ?
#

class mrp_production_workcenter_line(osv.osv):
    _inherit = 'mrp.production.workcenter.line'
    _columns = {
       'state': fields.selection([('draft','Draft'),('startworking', 'In Progress'),('pause','Pause'),('cancel','Canceled'),('done','Finished')],'Status', readonly=True),
       'date_planned': fields.related('production_id', 'date_planned', type='datetime', string='Date Planned'),
       'date_start': fields.datetime('Start Date'),
       'date_finnished': fields.datetime('End Date'),
       'delay': fields.char('Delay',size=128,help="This is delay between operation start and stop in this workcenter",readonly=True),
       'production_state':fields.related('production_id','state',type='char',string='Prod.State'),
       'product':fields.related('production_id','product_id',type='many2one',relation='product.product',string='Product'),
       'qty':fields.related('production_id','product_qty',type='float',string='Qty'),
       'uom':fields.related('production_id','product_uom',type='many2one',relation='product.uom',string='UOM'),
    }
    _defaults = {
        'state': lambda *a: 'draft',
        'delay': lambda *a: '0 Days 0 hrs  and 0 mins'
    }

    def modify_production_order_state(self,cr,uid,ids,action):
        wf_service = netsvc.LocalService("workflow")
        oper_obj=self.browse(cr,uid,ids)[0]
        prod_obj=oper_obj.production_id
        if action=='start':
               if prod_obj.state =='confirmed':
                   self.pool.get('mrp.production').force_production(cr, uid, [prod_obj.id])
                   wf_service.trg_validate(uid, 'mrp.production', prod_obj.id, 'button_produce', cr)
               elif prod_obj.state =='ready':
                   wf_service.trg_validate(uid, 'mrp.production', prod_obj.id, 'button_produce', cr)
               elif prod_obj.state =='in_production':
                   return
               else:
                   raise osv.except_osv(_('Error!'),_('Production Order Cannot start in [%s] state') % (prod_obj.state,))
        else:
            oper_ids=self.search(cr,uid,[('production_id','=',prod_obj.id)])
            obj=self.browse(cr,uid,oper_ids)
            flag=True
            for line in obj:
                if line.state!='done':
                     flag=False
            if flag:
                wf_service.trg_validate(uid, 'mrp.production', oper_obj.production_id.id, 'button_produce_done', cr)
        return

    def action_draft(self, cr, uid, ids):
        self.write(cr, uid, ids, {'state':'draft'})
        return True

    def action_start_working(self, cr, uid, ids):
        self.modify_production_order_state(cr,uid,ids,'start')
        self.write(cr, uid, ids, {'state':'startworking'})
        return True

    def action_done(self, cr, uid, ids):
        self.write(cr, uid, ids, {'state':'done'})
        self.modify_production_order_state(cr,uid,ids,'done')
        return True

    def action_cancel(self, cr, uid, ids):
        self.write(cr, uid, ids, {'state':'cancel'})
        return True

    def action_pause(self, cr, uid, ids):
        self.write(cr, uid, ids, {'state':'pause'})
        return True

    def action_resume(self, cr, uid, ids):
        self.write(cr, uid, ids, {'state':'startworking'})
        return True

mrp_production_workcenter_line()

class mrp_production(osv.osv):
    _name = 'mrp.production'
    _inherit = 'mrp.production'
    _description = 'Production'

    def action_production_end(self, cr, uid, ids):
        obj=self.browse(cr,uid,ids)[0]
        for workcenter_line in obj.workcenter_lines:
            tmp=self.pool.get('mrp.production.workcenter.line').action_done(cr,uid,[workcenter_line.id])
        return super(mrp_production,self).action_production_end(cr,uid,ids)

    def action_cancel(self, cr, uid, ids):
        obj=self.browse(cr,uid,ids)[0]
        for workcenter_line in obj.workcenter_lines:
            tmp=self.pool.get('mrp.production.workcenter.line').action_cancel(cr,uid,[workcenter_line.id])
        return super(mrp_production,self).action_cancel(cr,uid,ids)

mrp_production()

class mrp_operations_operation_code(osv.osv):
    _name="mrp_operations.operation.code"
    _columns={
        'name': fields.char('Operation Name',size=64, required=True),
        'code': fields.char('Code', size=16, required=True),
        'start_stop': fields.selection([('start','Start'),('pause','Pause'),('resume','Resume'),('cancel','Cancel'),('done','Done')], 'Status', required=True),
    }
mrp_operations_operation_code()

class mrp_operations_operation(osv.osv):
    _name="mrp_operations.operation"

    def _order_date_search_production(self, cr, uid, ids, context=None):
        operation_ids=self.pool.get('mrp_operations.operation').search(cr, uid, [('production_id','=',ids[0])], context=context)
        return operation_ids

    def _get_order_date(self, cr, uid, ids, field_name, arg, context):
        res={}
        operation_obj=self.browse(cr, uid, ids, context=context)
        for operation in operation_obj:
                res[operation.id]=operation.production_id.date_planned
        return res

    def calc_delay(self,cr,uid,vals):
        code_lst=[]
        time_lst=[]

        code_ids=self.pool.get('mrp_operations.operation.code').search(cr,uid,[('id','=',vals['code_id'])])
        code=self.pool.get('mrp_operations.operation.code').browse(cr,uid,code_ids)[0]

        oper_ids=self.search(cr,uid,[('production_id','=',vals['production_id']),('workcenter_id','=',vals['workcenter_id'])])
        oper_objs=self.browse(cr,uid,oper_ids)

        for oper in oper_objs:
            code_lst.append(oper.code_id.start_stop)
            time_lst.append(oper.date_start)

        code_lst.append(code.start_stop)
        time_lst.append(vals['date_start'])
        h=m=s=days=0
        for i in range(0,len(code_lst)):
            if code_lst[i]=='pause' or code_lst[i]=='done' or code_lst[i]=='cancel':
                if code_lst[i]=='cancel' and code_lst[i-1]=='pause':
                   continue
                a=datetime.datetime(int(time_lst[i-1][0:4]),int(time_lst[i-1][5:7]),int(time_lst[i-1][8:10]),int(time_lst[i-1][11:13]),int(time_lst[i-1][14:16]),int(time_lst[i-1][17:19]))
                b=datetime.datetime(int(time_lst[i][0:4]),int(time_lst[i][5:7]),int(time_lst[i][8:10]),int(time_lst[i][11:13]),int(time_lst[i][14:16]),int(time_lst[i][17:19]))
                diff =b-a
                min, sec = divmod(diff.seconds, 60)
                hrs, min = divmod(min, 60)
                days+=diff.days
                h+=hrs
                m+=min
                s+=sec
                if s>=60:
                    m+=1
                    s=0
                if m>=60:
                    h+=1
                    m=0
                if h>=24:
                    days+=1
                    h=0
        delay=str(days) +" Days "+ str(h) + " hrs  and " + str(m)+ " mins"
        return delay

    def check_operation(self,cr,uid,vals):
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
        oper_objs=self.browse(cr,uid,ids)[0]
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
        code=self.pool.get('mrp_operations.operation.code').browse(cr,uid,code_ids)[0]
        wc_op_id=self.pool.get('mrp.production.workcenter.line').search(cr,uid,[('workcenter_id','=',vals['workcenter_id']),('production_id','=',vals['production_id'])])
        if code.start_stop in ('start','done','pause','cancel','resume'):
            if not wc_op_id:
                production_obj=self.pool.get('mrp.production').browse(cr,uid,vals['production_id'])
                wc_op_id.append(self.pool.get('mrp.production.workcenter.line').create(cr,uid,{'production_id':vals['production_id'],'name':production_obj.product_id.name,'workcenter_id':vals['workcenter_id']}))
            if code.start_stop=='start':
                tmp=self.pool.get('mrp.production.workcenter.line').action_start_working(cr,uid,wc_op_id)
                wf_service.trg_validate(uid, 'mrp.production.workcenter.line', wc_op_id[0], 'button_start_working', cr)

            if code.start_stop=='done':
                tmp=self.pool.get('mrp.production.workcenter.line').action_done(cr,uid,wc_op_id)
                wf_service.trg_validate(uid, 'mrp.production.workcenter.line', wc_op_id[0], 'button_done', cr)
                self.pool.get('mrp.production').write(cr,uid,vals['production_id'],{'date_finnished':DateTime.now().strftime('%Y-%m-%d %H:%M:%S')})

            if code.start_stop=='pause':
                tmp=self.pool.get('mrp.production.workcenter.line').action_pause(cr,uid,wc_op_id)
                wf_service.trg_validate(uid, 'mrp.production.workcenter.line', wc_op_id[0], 'button_pause', cr)

            if code.start_stop=='resume':
                tmp=self.pool.get('mrp.production.workcenter.line').action_resume(cr,uid,wc_op_id)
                wf_service.trg_validate(uid, 'mrp.production.workcenter.line', wc_op_id[0], 'button_resume', cr)

            if code.start_stop=='cancel':
                tmp=self.pool.get('mrp.production.workcenter.line').action_cancel(cr,uid,wc_op_id)
                wf_service.trg_validate(uid, 'mrp.production.workcenter.line', wc_op_id[0], 'button_cancel', cr)

        if not self.check_operation(cr, uid, vals):
            return
        delay=self.calc_delay(cr, uid, vals)
        self.pool.get('mrp.production.workcenter.line').write(cr,uid,wc_op_id,{'delay':delay})

        return super(mrp_operations_operation, self).create(cr, uid, vals,  context=context)

    _columns={
        'production_id':fields.many2one('mrp.production','Production',required=True),
        'workcenter_id':fields.many2one('mrp.workcenter','Workcenter',required=True),
        'code_id':fields.many2one('mrp_operations.operation.code','Code',required=True),
        'date_start': fields.datetime('Start Date'),
        'date_finished': fields.datetime('End Date'),
        'order_date': fields.function(_get_order_date,method=True,string='Order Date',type='date',store={'mrp.production':(_order_date_search_production,['date_planned'], 10)}),
        }
    _defaults={
              'date_start': lambda *a:DateTime.now().strftime('%Y-%m-%d %H:%M:%S')
              }

mrp_operations_operation()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

