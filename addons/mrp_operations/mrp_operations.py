# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2005-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id: mrp.py 1292 2005-09-08 03:26:33Z pinky $
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

from osv import fields
from osv import osv
import ir

import netsvc
import time
from mx import DateTime

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
    _name = 'mrp.production.workcenter.line'
    _description = 'Production workcenters used'

    def _calc_delay(self, cr, uid, ids, name, arg, context={}):
        result = {}
        for obj in self.browse(cr, uid, ids, context):
            if obj.date_start and obj.date_finnished:
                diff = DateTime.strptime(obj.date_finnished, '%Y-%m-%d %H:%M:%S') - DateTime.strptime(obj.date_start, '%Y-%m-%d %H:%M:%S')
                result[obj.id]=diff.day
            else:
                result[obj.id] = 0
        return result

    _columns = {
        'state': fields.selection([('draft','Draft'),('confirm', 'Confirm'),('cancel','Canceled'),('done','Done')],'Status', readonly=True),
       'date_start': fields.datetime('Start Date'),
       'date_finnished': fields.datetime('End Date'),
       'delay': fields.function(_calc_delay, method=True, string='Delay', help="This is delay between operation start and stop in this workcenter"),
        'delay': fields.float('delay', required=True),


    }
    _defaults = {
        'state': lambda *a: 'draft',
        'delay': lambda *a: 0.0
    }

    def action_draft(self, cr, uid, ids):
        self.write(cr, uid, ids, {'state':'draft'})
#       self.write(cr, uid, ids, {'state':'draft','date_start':None})
        return True

    def action_confirm(self, cr, uid, ids):
        self.write(cr, uid, ids, {'state':'confirm'})
#       self.write(cr, uid, ids, {'state':'confirm','date_start':DateTime.now().strftime('%Y-%m-%d %H:%M:%S')})
        return True

    def action_done(self, cr, uid, ids):
        self.write(cr, uid, ids, {'state':'done'})
#       self.write(cr, uid, ids, {'state':'done','date_finnished':DateTime.now().strftime('%Y-%m-%d %H:%M:%S')})
        return True

    def action_cancel(self, cr, uid, ids):
        self.write(cr, uid, ids, {'state':'cancel'})
#       self.write(cr, uid, ids, {'state':'cancel','date_start':None})
        return True

mrp_production_workcenter_line()

class mrp_production(osv.osv):
    _name = 'mrp.production'
    _inherit = 'mrp.production'
    _description = 'Production'

    def action_confirm(self, cr, uid, ids):
        obj=self.browse(cr,uid,ids)[0]
        for workcenter_line in obj.workcenter_lines:
            tmp=self.pool.get('mrp.production.workcenter.line').action_confirm(cr,uid,[workcenter_line.id])
        return super(mrp_production,self).action_confirm(cr,uid,ids)

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
        'start_stop': fields.selection([('start','Start'),('stop','Stop'),('done','Done')], 'Status', required=True),
    }
mrp_operations_operation_code()

class mrp_operations_operation(osv.osv):
    _name="mrp_operations.operation"
    
    def _order_date_search_production(self,cr,uid,ids):
        operation_ids=self.pool.get('mrp_operations.operation').search(cr,uid,[('production_id','=',ids[0])])
        return operation_ids
        
    def _get_order_date(self, cr, uid, ids, field_name, arg, context):
        res={}
        operation_obj=self.browse(cr, uid, ids, context=context)
        for operation in operation_obj:
                res[operation.id]=operation.production_id.date_planned
        return res
    
    def create(self, cr, uid, vals, context=None):
        wf_service = netsvc.LocalService('workflow')
        code_ids=self.pool.get('mrp_operations.operation.code').search(cr,uid,[('id','=',vals['code_id'])])
        code=self.pool.get('mrp_operations.operation.code').browse(cr,uid,code_ids)[0]
        if code.start_stop=='start' or code.start_stop=='stop' or code.start_stop=='done':
            wc_op_id=self.pool.get('mrp.production.workcenter.line').search(cr,uid,[('workcenter_id','=',vals['workcenter_id']),('production_id','=',vals['production_id'])])
            if not wc_op_id:
                production_obj=self.pool.get('mrp.production').browse(cr,uid,vals['production_id'])
                wc_op_id.append(self.pool.get('mrp.production.workcenter.line').create(cr,uid,{'production_id':vals['production_id'],'name':production_obj.product_id.name,'workcenter_id':vals['workcenter_id']}))
            if code.start_stop=='start':
                tmp=self.pool.get('mrp.production.workcenter.line').action_confirm(cr,uid,wc_op_id[0])
            if code.start_stop=='done':
                tmp=self.pool.get('mrp.production.workcenter.line').action_done(cr,uid,wc_op_id)
            if code.start_stop=='stop':
                self.pool.get('mrp.production').write(cr,uid,vals['production_id'],{'date_finnished':DateTime.now().strftime('%Y-%m-%d %H:%M:%S')})
        return super(mrp_operations_operation, self).create(cr, uid, vals,  context=context)

    _columns={
        'production_id':fields.many2one('mrp.production','Production',required=True),
        'workcenter_id':fields.many2one('mrp.workcenter','Workcenter',required=True),
        'code_id':fields.many2one('mrp_operations.operation.code','Code',required=True),
        'date_start': fields.datetime('Start Date'),
        'date_finished': fields.datetime('End Date'),
        'order_date': fields.function(_get_order_date,method=True,string='Order Date',type='date',store={'mrp.production':(['date_planned'],_order_date_search_production)}),
        }

mrp_operations_operation()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

