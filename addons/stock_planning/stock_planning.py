# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
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

from osv import fields,osv
import pooler
from tools import config
import time
import netsvc
import math
import mx.DateTime
from mx.DateTime import RelativeDateTime, now, DateTime, localtime
from tools.translate import _

class stock_planning_period(osv.osv_memory):
    _name = "stock.planning.period"
    _description = "Create Planning Period"
    
    def _get_latest_period(self,cr,uid,context={}):
        cr.execute("select max(date_stop) from stock_period")
        result=cr.fetchone()        
        return result and result[0] or False

    _columns = {
        'name': fields.char('Period Name', size=64),
        'date_start': fields.date('Start Date', required=True),
        'date_stop': fields.date('End Date', required=True),
        'period_ids': fields.one2many('stock.period', 'planning_id', 'Periods'),
    }
    _defaults={
        'date_start':_get_latest_period,
    }
    
    def create_period_weekly(self,cr, uid, ids, context={}):
        res=self.create_period(cr, uid, ids, context, 6, 'Weekly')
        return {
                'view_type': 'form',
                "view_mode": 'tree',
                'res_model': 'stock.period',
                'type': 'ir.actions.act_window',                
            }
    
    def create_period_monthly(self,cr, uid, ids, context={},interval=1):
        for p in self.browse(cr, uid, ids, context):
            dt = p.date_start
            ds = mx.DateTime.strptime(p.date_start, '%Y-%m-%d')
            while ds.strftime('%Y-%m-%d')<p.date_stop:
                de = ds + RelativeDateTime(months=interval, days=-1)
                self.pool.get('stock.period').create(cr, uid, {
                    'name': ds.strftime('%Y/%m'),
                    'date_start': ds.strftime('%Y-%m-%d'),
                    'date_stop': de.strftime('%Y-%m-%d'),                    
                })
                ds = ds + RelativeDateTime(months=interval)
        return {
                'view_type': 'form',
                "view_mode": 'tree',
                'res_model': 'stock.period',
                'type': 'ir.actions.act_window',                
            }

    def create_period(self,cr, uid, ids, context={}, interval=0, name='Daily'):
        for p in self.browse(cr, uid, ids, context):
            dt = p.date_start
            ds = mx.DateTime.strptime(p.date_start, '%Y-%m-%d')            
            while ds.strftime('%Y-%m-%d')<p.date_stop:
                de = ds + RelativeDateTime(days=interval)
                if name=='Daily':
                    new_name=de.strftime('%Y-%m-%d')
                if name=="Weekly":
                    new_name=de.strftime('%Y, week %W')
                self.pool.get('stock.period').create(cr, uid, {
                    'name': new_name,
                    'date_start': ds.strftime('%Y-%m-%d'),
                    'date_stop': de.strftime('%Y-%m-%d'),
                })
                ds = ds + RelativeDateTime(days=interval) + 1
        return {
                'view_type': 'form',
                "view_mode": 'tree',
                'res_model': 'stock.period',
                'type': 'ir.actions.act_window',                
            }
stock_planning_period()


class stock_period(osv.osv):
    _name = "stock.period"
    _description = "Stock Period"
    
    _columns = {
        'name': fields.char('Period Name', size=64),
        'date_start': fields.datetime('Start Date', required=True),
        'date_stop': fields.datetime('End Date', required=True),        
        'state' : fields.selection([('draft','Draft'),('open','Open'),('close','Close')],'State')
    }
    _defaults = {
        'state' : lambda * a : 'draft'
    }
stock_period()


class stock_planning_sale_prevision(osv.osv):
    _name = "stock.planning.sale.prevision"
    _description = "Stock Planning Sale Prevision"
    
    def _get_real_amt_sold(self, cr, uid, ids, field, arg, context):
        res = {}
        for val in self.browse(cr, uid, ids):
            cr.execute("select sum(l.product_uom_qty) from sale_order_line l left join sale_order s on (s.id=l.order_id) where l.product_id = %s and s.state not in ('draft','cancel')", (val.product_id.id,))
            ret = cr.fetchall()
            res[val.id] = ret[0][0]
        return res
    
    _columns = {
        'name' : fields.char('Name', size=64),
        'user_id': fields.many2one('res.users' , 'Salesman',readonly=True, states={'draft':[('readonly',False)]}),
        'period_id': fields.many2one('stock.period' , 'Period', required=True),
        'product_id': fields.many2one('product.product' , 'Product', readonly=True, required=True,states={'draft':[('readonly',False)]}),
        'product_qty' : fields.float('Product Quantity', required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'product_amt' : fields.float('Product Amount', readonly=True, states={'draft':[('readonly',False)]}),
        'product_uom' : fields.many2one('product.uom', 'Product UoM', readonly=True, required=True, states={'draft':[('readonly',False)]}),
        'amt_sold' : fields.function(_get_real_amt_sold, method=True, string='Real Amount Sold'),
        'state' : fields.selection([('draft','Draft'),('validated','Validated')],'State',readonly=True),
    }
    _defaults = {
        'state': lambda *args: 'draft'
    }
    def action_validate(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {'state':'validated'})
        return True
    
    def unlink(self, cr, uid, ids, context={}):
        previsions = self.read(cr, uid, ids, ['state'])
        unlink_ids = []
        for t in previsions:
            if t['state'] in ('draft'):
                unlink_ids.append(t['id'])
            else:
                raise osv.except_osv(_('Invalid action !'), _('Cannot delete Validated Sale Previsions !'))
        osv.osv.unlink(self, cr, uid, unlink_ids,context=context)
        return True
    
    def product_id_change(self, cr, uid, ids, product, uom=False, product_qty = 0, product_amt = 0.0):
        if not product:
            return {'value': {'product_qty' : 0.0, 'product_uom': False},'domain': {'product_uom': []}}

        product_obj =  self.pool.get('product.product').browse(cr, uid, product)
        result = {}
        if not uom:
            result['product_uom'] = product_obj.uom_id.id
            domain = {'product_uom':
                        [('category_id', '=', product_obj.uom_id.category_id.id)],}
        if product_amt:
            result['product_qty'] = math.floor(product_amt/(product_obj.product_tmpl_id.list_price))
            
        return {'value': result}
    
stock_planning_sale_prevision()

class stock_planning(osv.osv):
    _name = "stock.planning"
    _description = "Stock Planning"
    
    def _get_product_qty(self, cr, uid, ids, field_names, arg, context):
        res = {}
        if not context:
            context = {}
        mapping = {
            'incoming': {
                'field': "incoming_qty",
                'adapter': lambda x: x,
            },
            'outgoing': {
                'field': "outgoing_qty",
                'adapter': lambda x: -x,
            },
        }

        for val in self.browse(cr, uid, ids):
            res[val.id] = {}
            context['from_date'] = val.period_id.date_start
            context['to_date'] = val.period_id.date_stop
            context['warehouse'] = val.warehouse_id.id or False
            product_obj =  self.pool.get('product.product').read(cr, uid,val.product_id.id,[], context)
            for fn in field_names:
                product_qty = product_obj[mapping[fn]['field']]
                res[val.id][fn] = mapping[fn]['adapter'](product_qty)
        return res
    
    def _get_planned_sale(self, cr, uid, ids, field_name, arg, context):
        res = {}
        for val in self.browse(cr, uid, ids):
            cr.execute('select sum(product_qty) from stock_planning_sale_prevision where product_id = %s and period_id = %s',(val.product_id.id,val.period_id.id))
            product_qty = cr.fetchall()[0][0]
            res[val.id] = product_qty
        return res
    
    def _get_stock_start(self, cr, uid, ids, field_name, arg, context):
        res = {}
        for val in self.browse(cr, uid, ids):
            res[val.id] = 0.0
            context['from_date'] = val.period_id.date_start
            context['to_date'] = val.period_id.date_stop
            context['warehouse'] = val.warehouse_id.id or False
            current_date =  time.strftime('%Y-%m-%d')
            product_obj =  self.pool.get('product.product').browse(cr, uid,val.product_id.id,[], context)
            if current_date > val.period_id.date_stop:
                pass
            elif current_date > val.period_id.date_start and current_date < val.period_id.date_stop:
                res[val.id] = product_obj.qty_available
            else:
                res[val.id] = product_obj.qty_available + (val.to_procure - val.planned_outgoing)
        return res
    
    def _get_value_left(self, cr, uid, ids, field_names, arg, context):
        res = {}
        for val in self.browse(cr, uid, ids):
            res[val.id] = {}
            if field_names[0] == 'incoming_left':
                ret = val.to_procure-val.incoming
            if  field_names[0] == 'outgoing_left':
                ret = val.planned_outgoing-val.outgoing
            res[val.id][field_names[0]] = ret
        return res
    
    def _get_past_future(self, cr, uid, ids, field_names, arg, context):
        res = {}
        for val in self.browse(cr, uid, ids):
            if val.period_id.date_stop < time.strftime('%Y-%m-%d'):
                res[val.id] = 'Past'
            else:
                res[val.id] = 'Future'
        return res
    
    def _get_period_id(self, cr, uid, context={}):
#        cr.execute()
        res = {}
        return res   


    _columns = {
        'name' : fields.char('Name', size=64),
        'state' : fields.selection([('draft','Draft'),('done','Done')],'State',readonly=True),
        'period_id': fields.many2one('stock.period' , 'Period', required=True),
        'product_id': fields.many2one('product.product' , 'Product', required=True),
        'product_uom' : fields.many2one('product.uom', 'UoM', required=True),
        'planned_outgoing' : fields.float('Forecast Out', required=True),
        'planned_sale': fields.function(_get_planned_sale, method=True, string='Sales Forecast'),
        'stock_start': fields.function(_get_stock_start, method=True, string='Stock Simulation'),
        'incoming': fields.function(_get_product_qty, method=True, type='float', string='Confirmed In', multi='incoming'),
        'outgoing': fields.function(_get_product_qty, method=True, type='float', string='Confirmed Out', multi='outgoing'),
        'incoming_left': fields.function(_get_value_left, method=True, string='Delta In', multi="stock_incoming_left"),
        'outgoing_left': fields.function(_get_value_left, method=True, string='Delta Out', multi="outgoing_left"),
        'to_procure': fields.float(string='Forecast In', required=True),
        'warehouse_id' : fields.many2one('stock.warehouse','Warehouse'),
        'line_time' : fields.function(_get_past_future, method=True,type='char', string='Past/Future'),
    }
    _defaults = {
        'state': lambda *args: 'draft' ,
        'period_id': _get_period_id
    }   
    
    _order = 'period_id'
    
    def procure_incomming_left(self, cr, uid, ids, context, *args):
        result = {}
        for obj in self.browse(cr, uid, ids):
            # source location is virtual procurement location for the product (will be mapped to supplier or
            # production location by mrp workflow)
            src_id = obj.product_id.property_stock_procurement and obj.product_id.property_stock_procurement.id
            # target location is input location of selected warehouse
            location_id = obj.warehouse_id and obj.warehouse_id.lot_input_id.id or False
            if location_id and src_id:
                move_id = self.pool.get('stock.move').create(cr, uid, {
                                'name': obj.product_id.name[:64],
                                'product_id': obj.product_id.id,
                                'date_planned': obj.period_id.date_start,
                                'product_qty': obj.incoming_left,
                                'product_uom': obj.product_uom.id,
                                'product_uos_qty': obj.incoming_left,
                                'product_uos': obj.product_uom.id,
                                'location_id': src_id,
                                'location_dest_id': location_id,
                                'state': 'waiting',
                            })
                proc_id = self.pool.get('mrp.procurement').create(cr, uid, {
                                'name': _('Procure Delta In From MPS'),
                                'origin': 'Stock Planning',
                                'date_planned': obj.period_id.date_start,
                                'product_id': obj.product_id.id,
                                'product_qty': obj.incoming_left,
                                'product_uom': obj.product_uom.id,
                                'product_uos_qty': obj.incoming_left,
                                'product_uos': obj.product_uom.id,
                                'location_id': location_id,
                                'procure_method': obj.product_id.product_tmpl_id.procure_method,
                                'move_id': move_id,
                            })
                wf_service = netsvc.LocalService("workflow")
                wf_service.trg_validate(uid, 'mrp.procurement', proc_id, 'button_confirm', cr)
                self.write(cr, uid, obj.id,{'state':'done'})
            else:
                raise osv.except_osv(_('Warning'), _('Please specify a warehouse to create the procurement'))
        return True
    
    
    def product_id_change(self, cr, uid, ids, product, uom=False):
        if not product:
            return {'value': { 'product_uom': False},'domain': {'product_uom': []}}
        product_obj =  self.pool.get('product.product').browse(cr, uid, product)
        result = {}
        if not uom:
            result['product_uom'] = product_obj.uom_id.id
            domain = {'product_uom':
                        [('category_id', '=', product_obj.uom_id.category_id.id)],}
        return {'value': result}
stock_planning()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
