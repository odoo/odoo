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

def rounding(fl, round_value):
    if not round_value:
        return fl
    return round(fl / round_value) * round_value


# Object creating periods quickly
# changed that stop_date is created with hour 23:59:00 when it was 00:00:00 stop date was excluded from period
class stock_period_createlines(osv.osv_memory):
    _name = "stock.period.createlines"

    def _get_new_period_start(self,cr,uid,context={}):
        cr.execute("select max(date_stop) from stock_period")
        result=cr.fetchone()
        last_date = result and result[0] or False
        if last_date:
            period_start = mx.DateTime.strptime(last_date,"%Y-%m-%d %H:%M:%S")+ RelativeDateTime(days=1)
            period_start = period_start - RelativeDateTime(hours=period_start.hour, minutes=period_start.minute, seconds=period_start.second)
        else:
            period_start = mx.DateTime.today()
        return period_start.strftime('%Y-%m-%d')
   

    _columns = {
        'name': fields.char('Period Name', size=64),
        'date_start': fields.date('Start Date', required=True),
        'date_stop': fields.date('End Date', required=True),
        'period_ids': fields.one2many('stock.period', 'planning_id', 'Periods'),
    }
    _defaults={
        'date_start':_get_new_period_start,
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
                de = ds + RelativeDateTime(months=interval, minutes=-1)
                self.pool.get('stock.period').create(cr, uid, {
                    'name': ds.strftime('%Y/%m'),
                    'date_start': ds.strftime('%Y-%m-%d'),
                    'date_stop': de.strftime('%Y-%m-%d %H:%M:%S'),                    
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
                de = ds + RelativeDateTime(days=interval, minutes =-1)
                if name=='Daily':
                    new_name=de.strftime('%Y-%m-%d')
                if name=="Weekly":
                    new_name=de.strftime('%Y, week %W')
                self.pool.get('stock.period').create(cr, uid, {
                    'name': new_name,
                    'date_start': ds.strftime('%Y-%m-%d'),
                    'date_stop': de.strftime('%Y-%m-%d %H:%M:%S'),
                })
                ds = ds + RelativeDateTime(days=interval) + 1
        return {
                'view_type': 'form',
                "view_mode": 'tree',
                'res_model': 'stock.period',
                'type': 'ir.actions.act_window',                
            }
stock_period_createlines()

# Periods have no company_id field as they can be shared across similar companies.
# If somone thinks different it can be improved.
class stock_period(osv.osv):
    _name = "stock.period"
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

# Creates forecasts records for products from selected Product Category for selected 'Warehouse - Period'
# Object added by contributor in ver 1.1
class stock_sale_forecast_createlines(osv.osv_memory):
    _name = "stock.sale.forecast.createlines"

# FIXME Add some period sugestion like below

#    def _get_latest_period(self,cr,uid,context={}):
#        cr.execute("select max(date_stop) from stock_period")
#        result=cr.fetchone()        
#        return result and result[0] or False
   

    _columns = {
        'company_id': fields.many2one('res.company', 'Company', required=True, select=1),
        'warehouse_id1': fields.many2one('stock.warehouse' , 'Warehouse', required=True, \
                                help='Warehouse which forecasts will concern. '\
                                   'If during stock planning you will need sales forecast for all warehouses choose any warehouse now.'),
        'period_id1': fields.many2one('stock.period' , 'Period', required=True, help = 'Period which forecasts will concern.' ),
        'product_categ_id1': fields.many2one('product.category' , 'Product Category', required=True, \
                                help ='Product Category of products which created forecasts will concern.'),
        'copy_forecast' : fields.boolean('Copy Last Forecast', help="Copy quantities from last Stock and Sale Forecast."),
    }

    _defaults = { 
        'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'stock.sale.forecast.createlines', context=c),
    }

    def create_forecast(self,cr, uid, ids, context={}):
        product_obj = self.pool.get('product.product')
        forecast_obj=self.pool.get('stock.sale.forecast')
        for f in self.browse(cr, uid, ids, context):
            prod_categ_obj=self.pool.get('product.category')
            template_obj=self.pool.get('product.template')
            categ_ids =  f.product_categ_id1.id and [f.product_categ_id1.id] or []
            prod_categ_ids=prod_categ_obj.search(cr,uid,[('parent_id','child_of',categ_ids)]) 
            templates_ids = template_obj.search(cr,uid,[('categ_id','in',prod_categ_ids)]) 
            products_ids = product_obj.search(cr,uid,[('product_tmpl_id','in',templates_ids)])
            if len(products_ids)==0:
                raise osv.except_osv(_('Error !'), _('No products in selected category !'))
            copy = f.copy_forecast
            for p in product_obj.browse(cr, uid, products_ids,{}):
                if len(forecast_obj.search(cr, uid, [('product_id','=',p.id) , \
                                                       ('period_id','=',f.period_id1.id), \
                                                       ('user_id','=',uid), \
                                                       ('warehouse_id','=',f.warehouse_id1.id)]))== 0:
                    forecast_qty = 0.0
# Not sure if it is expected quantity for this feature (copying forecast from previous period)
# because it can take incidental forecast of this warehouse, this product and this user (creating, writing or validating forecast).
# It takes only one forecast line (no sum). If user creates only one forecast per period it will be OK. If not I have no idea how to count it.
                    
                    prod_uom = False
                    if copy:
                        cr.execute("SELECT period.date_stop, forecast.product_qty, forecast.product_uom \
                                    FROM stock_sale_forecast AS forecast \
                                    LEFT JOIN stock_period AS period \
                                    ON forecast.period_id = period.id \
                                    WHERE (forecast.user_id = %s OR forecast.create_uid = %s OR forecast.write_uid = %s) \
                                        AND forecast.warehouse_id = %s AND forecast.product_id = %s \
                                        AND period.date_stop < %s \
                                    ORDER BY period.date_stop DESC",
                                    (uid, uid, uid, f.warehouse_id1.id, p.id, f.period_id1.date_stop) )
                        ret=cr.fetchone()
                        if ret:
                            forecast_qty = ret[1]        
                            prod_uom = ret[2]
                    prod_uom = prod_uom or p.uom_id.id
                    prod_uos_categ = False
                    if p.uos_id:
                        prod_uos_categ = p.uos_id.category_id.id
                    forecast_obj.create(cr, uid, {
                        'company_id'  : f.warehouse_id1.company_id.id,
                        'period_id': f.period_id1.id,
                        'warehouse_id': f.warehouse_id1.id,
                        'product_id': p.id,
                        'product_qty' : forecast_qty,
                        'product_amt' : 0.0,
                        'product_uom' : prod_uom,
                        'active_uom' : prod_uom,
                        'product_uom_categ' : p.uom_id.category_id.id,
                        'product_uos_categ' : prod_uos_categ,
                     })
        return {
                'view_type': 'form',
                "view_mode": 'tree',
                'res_model': 'stock.sale.forecast',
                'type': 'ir.actions.act_window',                
            }
stock_sale_forecast_createlines()


# Stock and Sales Forecast object. Previously stock_planning_sale_prevision.
# A lot of changes in 1.1
class stock_sale_forecast(osv.osv):
    _name = "stock.sale.forecast"
    
    _columns = {
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'create_uid':  fields.many2one('res.users', 'Responsible'),
        'name' : fields.char('Name', size=64, readonly=True, states={'draft':[('readonly',False)]}),
        'user_id': fields.many2one('res.users' , 'Created/Validated by',readonly=True, \
                                        help='Shows who created this forecast, or who validated.'),
        'warehouse_id': fields.many2one('stock.warehouse' , 'Warehouse', required=True, readonly=True, states={'draft':[('readonly',False)]}, \
                                        help='Shows which warehouse this forecast concerns. '\
                                         'If during stock planning you will need sales forecast for all warehouses choose any warehouse now.'),
        'period_id': fields.many2one('stock.period' , 'Period', required=True, readonly=True, states={'draft':[('readonly',False)]}, \
                                        help = 'Shows which period this forecast concerns.'),
        'product_id': fields.many2one('product.product' , 'Product', readonly=True, required=True, states={'draft':[('readonly',False)]}, \
                                        help = 'Shows which product this forecast concerns.'),
        'product_qty' : fields.float('Product Quantity', required=True, readonly=True, states={'draft':[('readonly',False)]}, \
                                        help= 'Forecasted quantity.'),
        'product_amt' : fields.float('Product Amount', readonly=True, states={'draft':[('readonly',False)]}, \
                                        help='Forecast value which will be converted to Product Quantity according to prices.'),
        'product_uom_categ' : fields.many2one('product.uom.categ', 'Product UoM Category'),  # Invisible field for product_uom domain
        'product_uom' : fields.many2one('product.uom', 'Product UoM', required=True, readonly=True, states={'draft':[('readonly',False)]}, \
                        help = "Unit of Measure used to show the quanities of stock calculation." \
                        "You can use units form default category or from second category (UoS category)."),
        'product_uos_categ' : fields.many2one('product.uom.categ', 'Product UoS Category'), # Invisible field for product_uos domain
# Field used in onchange_uom to check what uom was before change and recalculate quantities acording to old uom (active_uom) and new uom.
        'active_uom' :fields.many2one('product.uom',  string = "Active UoM"),  
        'state' : fields.selection([('draft','Draft'),('validated','Validated')],'State',readonly=True),
        'analyzed_period1_id' : fields.many2one('stock.period' , 'Period1', readonly=True, states={'draft':[('readonly',False)]},),
        'analyzed_period2_id' : fields.many2one('stock.period' , 'Period2', readonly=True, states={'draft':[('readonly',False)]},),
        'analyzed_period3_id' : fields.many2one('stock.period' , 'Period3', readonly=True, states={'draft':[('readonly',False)]},),
        'analyzed_period4_id' : fields.many2one('stock.period' , 'Period4', readonly=True, states={'draft':[('readonly',False)]},),
        'analyzed_period5_id' : fields.many2one('stock.period' , 'Period5', readonly=True, states={'draft':[('readonly',False)]},),
        'analyzed_user_id' : fields.many2one('res.users' , 'This User', required=False, readonly=True, states={'draft':[('readonly',False)]},),
        'analyzed_dept_id' : fields.many2one('hr.department' , 'This Department', required=False, \
                                    readonly=True, states={'draft':[('readonly',False)]},),
        'analyzed_warehouse_id' : fields.many2one('stock.warehouse' , 'This Warehouse', required=False, \
                                    readonly=True, states={'draft':[('readonly',False)]}),
        'analyze_company' : fields.boolean('Per Company', readonly=True, states={'draft':[('readonly',False)]}, \
                                    help = "Check this box to see the sales for whole company."),
        'analyzed_period1_per_user' : fields.float('This User Period1', readonly=True),
        'analyzed_period2_per_user' : fields.float('This User Period2', readonly=True),
        'analyzed_period3_per_user' : fields.float('This User Period3', readonly=True),
        'analyzed_period4_per_user' : fields.float('This User Period4', readonly=True),
        'analyzed_period5_per_user' : fields.float('This User Period5', readonly=True),
        'analyzed_period1_per_dept' : fields.float('This Dept Period1', readonly=True),
        'analyzed_period2_per_dept' : fields.float('This Dept Period2', readonly=True),
        'analyzed_period3_per_dept' : fields.float('This Dept Period3', readonly=True),
        'analyzed_period4_per_dept' : fields.float('This Dept Period4', readonly=True),
        'analyzed_period5_per_dept' : fields.float('This Dept Period5', readonly=True),
        'analyzed_period1_per_warehouse' : fields.float('This Warehouse Period1', readonly=True),
        'analyzed_period2_per_warehouse' : fields.float('This Warehouse Period2', readonly=True),
        'analyzed_period3_per_warehouse' : fields.float('This Warehouse Period3', readonly=True),
        'analyzed_period4_per_warehouse' : fields.float('This Warehouse Period4', readonly=True),
        'analyzed_period5_per_warehouse' : fields.float('This Warehouse Period5', readonly=True),
        'analyzed_period1_per_company' : fields.float('This Copmany Period1', readonly=True),
        'analyzed_period2_per_company' : fields.float('This Company Period2', readonly=True),
        'analyzed_period3_per_company' : fields.float('This Company Period3', readonly=True),
        'analyzed_period4_per_company' : fields.float('This Company Period4', readonly=True),
        'analyzed_period5_per_company' : fields.float('This Company Period5', readonly=True),
    }
    _defaults = {
        'user_id': lambda obj, cr, uid, context: uid,
        'state': lambda *args: 'draft',
        'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'stock.sale.forecast', context=c),
    }

    def action_validate(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {'state':'validated','user_id':uid})
        return True
    
    def unlink(self, cr, uid, ids, context={}):
        forecasts = self.read(cr, uid, ids, ['state'])
        unlink_ids = []
        for t in forecasts:
            if t['state'] in ('draft'):
                unlink_ids.append(t['id'])
            else:
                raise osv.except_osv(_('Invalid action !'), _('Cannot delete Validated Sale Forecasts !'))
        osv.osv.unlink(self, cr, uid, unlink_ids,context=context)
        return True

    def onchange_company(self, cr, uid, ids, company_id):
        result = {}
        if company_id:
            result['warehouse_id'] = False
            result['analyzed_user_id'] = False
            result['analyzed_dept_id'] = False
            result['analyzed_warehouse_id'] = False
        return {'value': result}

    def product_id_change(self, cr, uid, ids, product_id):
        ret={}
        if product_id:
            product_rec =  self.pool.get('product.product').browse(cr, uid, product_id)
            ret['product_uom'] = product_rec.uom_id.id
            ret['product_uom_categ'] = product_rec.uom_id.category_id.id
            ret['product_uos_categ'] = product_rec.uos_id and product_rec.uos_id.category_id.id or False
            ret['active_uom'] = product_rec.uom_id.id
        else:
            ret['product_uom'] = False
            ret['product_uom_categ'] = False
            ret['product_uos_categ'] = False
        res = {'value': ret}
        return res

    def onchange_uom(self, cr, uid, ids, product_uom=False, product_qty=0.0, active_uom=False ):
        ret={}
        val1 = self.browse(cr, uid, ids)
        val = val1[0]
        coeff_uom2def = self._to_default_uom_factor(cr, uid, val, active_uom, {})
        coeff_def2uom, round_value = self._from_default_uom_factor( cr, uid, val, product_uom, {})
        coeff = coeff_uom2def * coeff_def2uom
        ret['product_qty'] = rounding(coeff * product_qty, round_value)
        ret['active_uom'] = product_uom
        return {'value': ret}

    def product_amt_change(self, cr, uid, ids, product_amt = 0.0, product_uom=False):
        ret={}
        if product_amt:
            coeff_def2uom = 1
            val1 = self.browse(cr, uid, ids)
            val = val1[0]
            if (product_uom != val.product_id.uom_id.id):
                coeff_def2uom, rounding = self._from_default_uom_factor( cr, uid, val, product_uom, {})
            ret['product_qty'] = rounding(coeff_def2uom * product_amt/(val.product_id.product_tmpl_id.list_price), round_value)
        res = {'value': ret}
        return res

    def _to_default_uom_factor(self, cr, uid, val, uom_id, context):
        uom_obj = self.pool.get('product.uom')
        uom = uom_obj.browse(cr, uid, uom_id, context=context)
        coef =  uom.factor
        if uom.category_id.id <> val.product_id.uom_id.category_id.id:
            coef = coef / val.product_id.uos_coeff
        return val.product_id.uom_id.factor / coef

    def _from_default_uom_factor(self, cr, uid, val, uom_id, context):
        uom_obj = self.pool.get('product.uom')
        uom = uom_obj.browse(cr, uid, uom_id, context=context)
        res = uom.factor
        if uom.category_id.id <> val.product_id.uom_id.category_id.id:
            res = res / val.product_id.uos_coeff
        return res / val.product_id.uom_id.factor, uom.rounding

    def _sales_per_users(self, cr, uid, so, so_line, company, users):
        cr.execute("SELECT sum(sol.product_uom_qty) FROM sale_order_line AS sol LEFT JOIN sale_order AS s ON (s.id = sol.order_id) " \
                   "WHERE (sol.id IN (%s)) AND (s.state NOT IN (\'draft\',\'cancel\')) AND (s.id IN (%s)) AND (s.company_id=%s) " \
                    "AND (s.user_id IN (%s)) " %(so_line, so, company, users))
        ret = cr.fetchone()[0] or 0.0
        return ret

    def _sales_per_warehouse(self, cr, uid, so, so_line, company, shops):        
        cr.execute("SELECT sum(sol.product_uom_qty) FROM sale_order_line AS sol LEFT JOIN sale_order AS s ON (s.id = sol.order_id) " \
                   "WHERE (sol.id IN (%s)) AND (s.state NOT IN (\'draft\',\'cancel\')) AND (s.id IN (%s))AND (s.company_id=%s) " \
                    "AND (s.shop_id IN (%s))" %(so_line, so, company, shops))
        ret = cr.fetchone()[0] or 0.0
        return ret

    def _sales_per_company(self, cr, uid, so, so_line, company, ):
        cr.execute("SELECT sum(sol.product_uom_qty) FROM sale_order_line AS sol LEFT JOIN sale_order AS s ON (s.id = sol.order_id) " \
                   "WHERE (sol.id IN (%s)) AND (s.state NOT IN (\'draft\',\'cancel\')) AND (s.id IN (%s)) AND (s.company_id=%s)"%(so_line, so, company))
        ret = cr.fetchone()[0] or 0.0
        return ret
    
    def calculate_sales_history(self, cr, uid, ids, context, *args):
        sales=[[0,0,0,0],[0,0,0,0],[0,0,0,0],[0,0,0,0],[0,0,0,0],]
        for obj in  self.browse(cr, uid, ids):
            periods =obj.analyzed_period1_id, obj.analyzed_period2_id, obj.analyzed_period3_id, obj.analyzed_period4_id, obj.analyzed_period5_id
            so_obj = self.pool.get('sale.order')
            so_line_obj= self.pool.get('sale.order.line')
            so_line_product_ids = so_line_obj.search(cr, uid, [('product_id','=', obj.product_id.id)], context = context)
            if so_line_product_ids:
                so_line_product_set = ','.join(map(str,so_line_product_ids))
                if obj.analyzed_warehouse_id:
                    shops = self.pool.get('sale.shop').search(cr, uid,[('warehouse_id','=', obj.analyzed_warehouse_id.id)], context = context)
                    shops_set = ','.join(map(str,shops))
                else:
                    shops = False
                if obj.analyzed_dept_id:
                    dept_obj = self.pool.get('hr.department')
                    dept_id =  obj.analyzed_dept_id.id and [obj.analyzed_dept_id.id] or []
                    dept_ids = dept_obj.search(cr,uid,[('parent_id','child_of',dept_id)])
                    dept_ids_set = ','.join(map(str,dept_ids))
                    cr.execute("SELECT user_id FROM hr_department_user_rel WHERE (department_id IN (%s))" %(dept_ids_set))
                    dept_users = [x for x, in cr.fetchall()]
                    dept_users_set =  ','.join(map(str,dept_users))
                else:
                    dept_users = False
                factor, round_value = self._from_default_uom_factor(cr, uid, obj, obj.product_uom.id, context=context)
                for i, period in enumerate(periods):
                    if period:
                        so_period_ids = so_obj.search(cr, uid, [('date_order','>=',period.date_start), ('date_order','<=',period.date_stop)], context = context)
                        if so_period_ids:
                            so_period_set = ','.join(map(str,so_period_ids))
                            if obj.analyzed_user_id:
                                user_set = str(obj.analyzed_user_id.id)
                                sales[i][0] =self._sales_per_users(cr, uid, so_period_set, so_line_product_set, obj.company_id.id, user_set)
                                sales[i][0] *=factor
                            if dept_users:
                                sales[i][1]=  self._sales_per_users(cr, uid, so_period_set,  so_line_product_set, obj.company_id.id, dept_users_set)
                                sales[i][1]*=factor
                            if shops:
                                sales[i][2]= self._sales_per_warehouse(cr, uid, so_period_set,  so_line_product_set, obj.company_id.id, shops_set)
                                sales[i][2]*=factor
                            if obj.analyze_company:
                                sales[i][3]= self._sales_per_company(cr, uid, so_period_set, so_line_product_set, obj.company_id.id, )
                                sales[i][3]*=factor
        self.write(cr, uid, ids, {
            'analyzed_period1_per_user':sales[0][0],
            'analyzed_period2_per_user':sales[1][0],
            'analyzed_period3_per_user':sales[2][0],
            'analyzed_period4_per_user':sales[3][0],
            'analyzed_period5_per_user':sales[4][0],
            'analyzed_period1_per_dept':sales[0][1],
            'analyzed_period2_per_dept':sales[1][1],
            'analyzed_period3_per_dept':sales[2][1],
            'analyzed_period4_per_dept':sales[3][1],
            'analyzed_period5_per_dept':sales[4][1],
            'analyzed_period1_per_warehouse':sales[0][2],
            'analyzed_period2_per_warehouse':sales[1][2],
            'analyzed_period3_per_warehouse':sales[2][2],
            'analyzed_period4_per_warehouse':sales[3][2],
            'analyzed_period5_per_warehouse':sales[4][2],
            'analyzed_period1_per_company':sales[0][3],
            'analyzed_period2_per_company':sales[1][3],
            'analyzed_period3_per_company':sales[2][3],
            'analyzed_period4_per_company':sales[3][3],
            'analyzed_period5_per_company':sales[4][3],
        })
        return True


stock_sale_forecast()

# Creates stock planning records for products from selected Product Category for selected 'Warehouse - Period' 
# Object added by contributor in ver 1.1 
class stock_planning_createlines(osv.osv_memory):
    _name = "stock.planning.createlines"

    def onchange_company(self, cr, uid, ids, company_id):
        result = {}
        if company_id:
            result['warehouse_id2'] = False
        return {'value': result}

    _columns = {
        'company_id': fields.many2one('res.company', 'Company', required = True),
        'period_id2': fields.many2one('stock.period' , 'Period', required=True, help = 'Period which planning will concern.'),
        'warehouse_id2': fields.many2one('stock.warehouse' , 'Warehouse', required=True, help = 'Warehouse which planning will concern.'),
        'product_categ_id2': fields.many2one('product.category' , 'Product Category', \
                        help = 'Planning will be created for products from Product Category selected by this field. '\
                               'This field is ignored when you check \"All Forecasted Product\" box.' ),
        'forecasted_products': fields.boolean('All Products with Forecast', \
                     help = "Check this box to create planning for all products having any forecast for selected Warehouse and Period. "\
                            "Product Category field will be ignored."),
    }

    _defaults = {
        'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'stock.planning', context=c),
    }

    def create_planning(self,cr, uid, ids, context={}):
        product_obj = self.pool.get('product.product')
        planning_obj=self.pool.get('stock.planning')

        for f in self.browse(cr, uid, ids, context=context):
            if f.forecasted_products:
                cr.execute("SELECT product_id \
                                FROM stock_sale_forecast \
                                WHERE (period_id = %s) AND (warehouse_id = %s)", (f.period_id2.id, f.warehouse_id2.id))
                products_id1 = [x for x, in cr.fetchall()]
            else:
                prod_categ_obj=self.pool.get('product.category')
                template_obj=self.pool.get('product.template')
                categ_ids =  f.product_categ_id2.id and [f.product_categ_id2.id] or []
                prod_categ_ids=prod_categ_obj.search(cr,uid,[('parent_id','child_of',categ_ids)]) 
                templates_ids = template_obj.search(cr,uid,[('categ_id','in',prod_categ_ids)]) 
                products_id1 = product_obj.search(cr,uid,[('product_tmpl_id','in',templates_ids)])
            if len(products_id1)==0:
                raise osv.except_osv(_('Error !'), _('No forecasts for selected period or no products in selected category !'))

            for p in product_obj.browse(cr, uid, products_id1,context=context):
                if len(planning_obj.search(cr, uid, [('product_id','=',p.id),
                                                      ('period_id','=',f.period_id2.id),
                                                      ('warehouse_id','=',f.warehouse_id2.id)]))== 0:
                    cr.execute("SELECT period.date_stop, planning.product_uom, planning.planned_outgoing, planning.to_procure, \
                                    planning.stock_only, planning.procure_to_stock, planning.confirmed_forecasts_only, \
                                    planning.supply_warehouse_id, planning.stock_supply_location \
                                FROM stock_planning AS planning \
                                LEFT JOIN stock_period AS period \
                                ON planning.period_id = period.id \
                                WHERE (planning.create_uid = %s OR planning.write_uid = %s) \
                                     AND planning.warehouse_id = %s AND planning.product_id = %s \
                                     AND period.date_stop < %s \
                                ORDER BY period.date_stop DESC",
                                    (uid, uid, f.warehouse_id2.id, p.id, f.period_id2.date_stop) )
                    ret=cr.fetchone()
#                        forecast_qty = ret and ret[0] or 0.0
                    if ret:
#                            raise osv.except_osv(_('Error !'), _('ret is %s %s %s %s %s %s')%(ret[0],ret[2],ret[3],ret[4],ret[5],ret[6],))
                        prod_uom = ret[1]
                        planned_out = ret[2]        
                        to_procure = ret[3]
                        stock_only = ret[4]
                        procure_to_stock = ret[5]
                        confirmed_forecasts_only = ret[6]
                        supply_warehouse_id = ret[7]
                        stock_supply_location = ret[8]
                    else:
                        prod_uom = p.uom_id.id
                        planned_out = False        
                        to_procure = False
                        stock_only = False
                        procure_to_stock = False
                        confirmed_forecasts_only = False
                        supply_warehouse_id = False
                        stock_supply_location = False
                    prod_uos_categ = False
                    if p.uos_id:
                        prod_uos_categ = p.uos_id.category_id.id
                    planning_obj.create(cr, uid, {
                        'company_id' : f.warehouse_id2.company_id.id,
                        'period_id': f.period_id2.id,
                        'warehouse_id' : f.warehouse_id2.id,
                        'product_id': p.id,
                        'product_uom' : prod_uom,
                        'product_uom_categ' : p.uom_id.category_id.id,
                        'product_uos_categ' : prod_uos_categ,
                        'active_uom' : prod_uom,
                        'planned_outgoing': planned_out,       
                        'to_procure': to_procure,
                        'stock_only': stock_only,
                        'procure_to_stock': procure_to_stock,
                        'confirmed_forecasts_only': confirmed_forecasts_only,
                        'supply_warehouse_id': supply_warehouse_id,
                        'stock_supply_location': stock_supply_location,

                    })
        return {
                'view_type': 'form',
                "view_mode": 'tree',
                'res_model': 'stock.planning',
                'type': 'ir.actions.act_window',                
            }
stock_planning_createlines()


# The main Stock Planning object
# A lot of changes by contributor in ver 1.1
class stock_planning(osv.osv):
    _name = "stock.planning"
    
    def _get_in_out(self, cr, uid, val, date_start, date_stop, direction, done, context):
#        res = {}
#        if not context:
#            context = {}
        mapping = {'in': {
                        'field': "incoming_qty",
                        'adapter': lambda x: x,
                  },
                  'out': {
                        'field': "outgoing_qty",
                        'adapter': lambda x: -x,
                  },
        }
        context['from_date'] = date_start
        context['to_date'] = date_stop
        locations = [val.warehouse_id.lot_stock_id.id,]
        if not val.stock_only:
            locations.extend([val.warehouse_id.lot_input_id.id, val.warehouse_id.lot_output_id.id])
        context['location'] = locations
        context['compute_child'] = True
        product_obj =  self.pool.get('product.product')
        prod_id = val.product_id.id
        if done:
            c1=context.copy()
            c1.update({ 'states':('done',), 'what':(direction,) })
            prod_ids = [prod_id]
            st = product_obj.get_product_available(cr,uid, prod_ids, context=c1)
            res = mapping[direction]['adapter'](st.get(prod_id,0.0))
        else:
            product=product_obj.read(cr, uid, prod_id,[], context)
            product_qty = product[mapping[direction]['field']]
            res = mapping[direction]['adapter'](product_qty)
#            res[val.id] = product_obj['incoming_qty']
        return res

    def _get_outgoing_before(self, cr, uid, val, date_start, date_stop, context):
        cr.execute("SELECT sum(planning.planned_outgoing), planning.product_uom \
                    FROM stock_planning AS planning \
                    LEFT JOIN stock_period AS period \
                    ON (planning.period_id = period.id) \
                    WHERE (period.date_stop >= %s) AND (period.date_stop <= %s) \
                        AND (planning.product_id = %s) AND (planning.company_id = %s) \
                    GROUP BY planning.product_uom", \
                        (date_start, date_stop, val.product_id.id, val.company_id.id,))
        planning_qtys = cr.fetchall()
        res = self._to_planning_uom(cr, uid, val, planning_qtys, context)
        return res

    def _to_planning_uom(self, cr, uid, val, qtys, context):
        res_qty = 0
        if qtys:
            uom_obj = self.pool.get('product.uom')
            for qty, prod_uom in qtys:
                coef = self._to_default_uom_factor(cr, uid, val, prod_uom, context=context)
                res_coef, round_value = self._from_default_uom_factor(cr, uid, val, val.product_uom.id, context=context)
                coef = coef * res_coef
                res_qty += rounding(qty * coef, round_value)
        return res_qty
        

    def _get_forecast(self, cr, uid, ids, field_names, arg, context):
        res = {}
        for val in self.browse(cr, uid, ids):
            res[val.id]={}
            valid_part = val.confirmed_forecasts_only and " AND state = 'validated'" or ""
            cr.execute('SELECT sum(product_qty), product_uom  \
                        FROM stock_sale_forecast \
                        WHERE product_id = %s AND period_id = %s AND company_id = %s '+valid_part+ \
                       'GROUP BY product_uom', \
                            (val.product_id.id,val.period_id.id, val.company_id.id))
            company_qtys = cr.fetchall()
            res[val.id]['company_forecast'] = self._to_planning_uom(cr, uid, val, company_qtys, context)

            cr.execute('SELECT sum(product_qty), product_uom \
                        FROM stock_sale_forecast \
                        WHERE product_id = %s and period_id = %s AND warehouse_id = %s ' + valid_part + \
                       'GROUP BY product_uom', \
                        (val.product_id.id,val.period_id.id, val.warehouse_id.id))
            warehouse_qtys = cr.fetchall()
            res[val.id]['warehouse_forecast'] = self._to_planning_uom(cr, uid, val, warehouse_qtys, context)
            res[val.id]['warehouse_forecast'] = rounding(res[val.id]['warehouse_forecast'],  val.product_id.uom_id.rounding)
        return res

    def _get_stock_start(self, cr, uid, val, date, context):
        context['from_date'] = None
        context['to_date'] = date
        locations = [val.warehouse_id.lot_stock_id.id,]
        if not val.stock_only:
            locations.extend([val.warehouse_id.lot_input_id.id, val.warehouse_id.lot_output_id.id])
        context['location'] = locations
        context['compute_child'] = True
        product_obj =  self.pool.get('product.product').read(cr, uid,val.product_id.id,[], context)
        res = product_obj['qty_available']     # value for stock_start
        return res
    
    def _get_past_future(self, cr, uid, ids, field_names, arg, context):
        res = {}
        for val in self.browse(cr, uid, ids, context=context):
            if val.period_id.date_stop < time.strftime('%Y-%m-%d'):
                res[val.id] = 'Past'
            else:
                res[val.id] = 'Future'
        return res

    def _get_op(self, cr, uid, ids, field_names, arg, context):  # op = OrderPoint
        res = {}
        for val in self.browse(cr, uid, ids, context=context):
            res[val.id]={}
            cr.execute("SELECT product_min_qty, product_max_qty, product_uom  \
                        FROM stock_warehouse_orderpoint \
                        WHERE warehouse_id = %s AND product_id = %s AND active = 'TRUE'", (val.warehouse_id.id, val.product_id.id))
            ret =  cr.fetchone() or [0.0,0.0,False]
            coef = 1
            round_value = 1
            if ret[2]:
                coef = self._to_default_uom_factor(cr, uid, val, ret[2], context)
                res_coef, round_value = self._from_default_uom_factor(cr, uid, val, val.product_uom.id, context=context)
                coef = coef * res_coef
            res[val.id]['minimum_op'] = rounding(ret[0]*coef, round_value)
            res[val.id]['maximum_op'] = ret[1]*coef
        return res
    
    def onchange_company(self, cr, uid, ids, company_id):
        result = {}
        if company_id:
            result['warehouse_id'] = False
        return {'value': result}

    def onchange_uom(self, cr, uid, ids, product_uom, ):
        if not product_uom:
            return {}
        ret={}
        val1 = self.browse(cr, uid, ids)
        val = val1[0]
        coeff_uom2def = self._to_default_uom_factor(cr, uid, val, val.active_uom.id, {})
        coeff_def2uom, round_value = self._from_default_uom_factor( cr, uid, val, product_uom, {})
        coeff = coeff_uom2def * coeff_def2uom
        ret['planned_outgoing'] = rounding(coeff * val.planned_outgoing, round_value)
        ret['to_procure'] = rounding(coeff * val.to_procure, round_value)
        ret['active_uom'] = product_uom
        return {'value': ret}

    _columns = {
        'company_id': fields.many2one('res.company', 'Company', required = True),
        'history' : fields.text('Procurement History', readonly=True, help = "History of procurement or internal supply of this planning line."),
        'state' : fields.selection([('draft','Draft'),('done','Done')],'State',readonly=True),
        'period_id': fields.many2one('stock.period' , 'Period', required=True, \
                help = 'Period for this planning. Requisition will be created for beginning of the period.'),
        'warehouse_id' : fields.many2one('stock.warehouse','Warehouse', required=True), 
        'product_id': fields.many2one('product.product' , 'Product', required=True, help = 'Product which this planning is created for.'),
        'product_uom_categ' : fields.many2one('product.uom.categ', 'Product UoM Category'), # Invisible field for product_uom domain
        'product_uom' : fields.many2one('product.uom', 'UoM', required=True, help = "Unit of Measure used to show the quanities of stock calculation." \
                        "You can use units form default category or from second category (UoS category)."),
        'product_uos_categ' : fields.many2one('product.uom.categ', 'Product UoM Category'), # Invisible field for product_uos domain
# Field used in onchange_uom to check what uom was before change to recalculate quantities acording to old uom (active_uom) and new uom.
        'active_uom' :fields.many2one('product.uom',  string = "Active UoM"), 
        'planned_outgoing' : fields.float('Planned Out', required=True,  \
                help = 'Enter planned outgoing quantity from selected Warehouse during the selected Period of selected Product. '\
                        'To plan this value look at Confirmed Out or Sales Forecasts. This value should be equal or greater than Confirmed Out.'),
        'company_forecast': fields.function(_get_forecast, method=True, string ='Company Forecast', multi = 'company', \
                help = 'All sales forecasts for whole company (for all Warehouses) of selected Product during selected Period.'),
        'warehouse_forecast': fields.function(_get_forecast, method=True, string ='Warehouse Forecast',  multi = 'warehouse',\
                help = 'All sales forecasts for selected Warehouse of selected Product during selected Period.'),
        'stock_simulation': fields.float('Stock Simulation', readonly =True, \
                help = 'Stock simulation at the end of selected Period.\n For current period it is: \n' \
                       'Initial Stock - Already Out + Already In - Expected Out + Incoming Left.\n' \
                        'For periods ahead it is: \nInitial Stock - Planned Out Before + Incoming Before - Planned Out + Planned In.'),
        'incoming': fields.float('Confirmed In', readonly=True, \
                help = 'Quantity of all confirmed incoming moves in calculated Period.'),
        'outgoing': fields.float('Confirmed Out', readonly=True, \
                help = 'Quantity of all confirmed outgoing moves in calculated Period.'),
        'incoming_left': fields.float('Incoming Left', readonly=True,  \
                help = 'Quantity left to Planned incoming quantity. This is calculated difference between Planned In and Confirmed In. ' \
                        'For current period Already In is also calculated. This value is used to create procurement for lacking quantity.'),
        'outgoing_left': fields.float('Expected Out', readonly=True, \
                help = 'Quantity expected to go out in selected period. As a difference between Planned Out and Confirmed Out. ' \
                        'For current period Already Out is also calculated'),
        'to_procure': fields.float(string='Planned In', required=True, \
                help = 'Enter quantity which (by your plan) should come in. Change this value and observe Stock simulation. ' \
                        'This value should be equal or greater than Confirmed In.'),
        'line_time' : fields.function(_get_past_future, method=True,type='char', string='Past/Future'),
        'minimum_op' : fields.function(_get_op, method=True, type='float', string = 'Minimum Rule', multi= 'minimum', \
                            help = 'Minimum quantity set in Minimum Stock Rules for this Warhouse'),
        'maximum_op' : fields.function(_get_op, method=True, type='float', string = 'Maximum Rule', multi= 'maximum', \
                            help = 'Maximum quantity set in Minimum Stock Rules for this Warhouse'),
        'outgoing_before' : fields.float('Planned Out Before', readonly=True, \
                            help= 'Planned Out in periods before calculated. '\
                                    'Between start date of current period and one day before start of calculated period.'),
        'incoming_before': fields.float('Incoming Before', readonly = True, \
                            help= 'Confirmed incoming in periods before calculated (Including Already In). '\
                                    'Between start date of current period and one day before start of calculated period.'),
        'stock_start' : fields.float('Initial Stock', readonly=True, \
                            help= 'Stock quantity one day before current period.'),
        'already_out' : fields.float('Already Out', readonly=True, \
                            help= 'Quantity which is already dispatched out of this warehouse in current period.'),
        'already_in' : fields.float('Already In', readonly=True, \
                            help= 'Quantity which is already picked up to this warehouse in current period.'),
        'stock_only' : fields.boolean("Stock Location Only", help = "Check to calculate stock location of selected warehouse only. " \
                                        "If not selected calculation is made for input, stock and output location of warehouse."),
        "procure_to_stock" : fields.boolean("Procure To Stock Location", help = "Chect to make procurement to stock location of selected warehouse. " \
                                        "If not selected procurement will be made into input location of warehouse."),
        "confirmed_forecasts_only" : fields.boolean("Validated Forecasts", help = "Check to take validated forecasts only. " \
                    "If not checked system takes validated and draft forecasts."),
        'supply_warehouse_id' : fields.many2one('stock.warehouse','Source Warehouse', help = "Warehouse used as source in supply pick move created by 'Supply from Another Warhouse'."), 
        "stock_supply_location" : fields.boolean("Stock Supply Location", help = "Check to supply from Stock location of Supply Warehouse. " \
                "If not checked supply will be made from Output location of Supply Warehouse. Used in 'Supply from Another Warhouse' with Supply Warehouse."),

    }

    _defaults = {
        'state': lambda *args: 'draft' ,
        'to_procure' : 0.0,
        'planned_outgoing' : 0.0,
        'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'stock.planning', context=c),
    }   
    
    _order = 'period_id'

    def _to_default_uom_factor(self, cr, uid, val, uom_id, context):
        uom_obj = self.pool.get('product.uom')
        uom = uom_obj.browse(cr, uid, uom_id, context=context)
        coef =  uom.factor
        if uom.category_id.id != val.product_id.uom_id.category_id.id:
            coef = coef / val.product_id.uos_coeff
        return val.product_id.uom_id.factor / coef


    def _from_default_uom_factor(self, cr, uid, val, uom_id, context):
        uom_obj = self.pool.get('product.uom')
        uom = uom_obj.browse(cr, uid, uom_id, context=context)
        res = uom.factor
        if uom.category_id.id != val.product_id.uom_id.category_id.id:
            res = res / val.product_id.uos_coeff
        return res / val.product_id.uom_id.factor, uom.rounding

    def calculate_planning(self, cr, uid, ids, context, *args):
        one_minute = RelativeDateTime(minutes=1)
        current_date_beginning_c = mx.DateTime.today()
        current_date_end_c = current_date_beginning_c  + RelativeDateTime(days=1, minutes=-1)  # to get hour 23:59:00 
        current_date_beginning = current_date_beginning_c.strftime('%Y-%m-%d %H:%M:%S')
        current_date_end = current_date_end_c.strftime('%Y-%m-%d %H:%M:%S')
        for val in self.browse(cr, uid, ids, context=context):
            day = mx.DateTime.strptime(val.period_id.date_start, '%Y-%m-%d %H:%M:%S')
            dbefore = mx.DateTime.DateTime(day.year, day.month, day.day) - one_minute
            day_before_calculated_period = dbefore.strftime('%Y-%m-%d %H:%M:%S')   # one day before start of calculated period
            cr.execute("SELECT date_start \
                    FROM stock_period AS period \
                    LEFT JOIN stock_planning AS planning \
                    ON (planning.period_id = period.id) \
                    WHERE (period.date_stop >= %s) AND (period.date_start <= %s) AND \
                        planning.product_id = %s", (current_date_end, current_date_end, val.product_id.id,)) #
            date = cr.fetchone()
            start_date_current_period = date and date[0] or False
            start_date_current_period = start_date_current_period or current_date_beginning
            day = mx.DateTime.strptime(start_date_current_period, '%Y-%m-%d %H:%M:%S')
            dbefore = mx.DateTime.DateTime(day.year, day.month, day.day) - one_minute
            date_for_start = dbefore.strftime('%Y-%m-%d %H:%M:%S')   # one day before current period
            already_out = self._get_in_out(cr, uid, val, start_date_current_period, current_date_end, direction='out', done = True, context=context),
            already_in = self._get_in_out(cr, uid, val, start_date_current_period, current_date_end, direction='in', done = True, context=context),
            outgoing = self._get_in_out(cr, uid, val, val.period_id.date_start, val.period_id.date_stop, direction='out', done = False, context=context),
            incoming = self._get_in_out(cr, uid, val, val.period_id.date_start, val.period_id.date_stop, direction='in', done = False, context=context),
            outgoing_before = self._get_outgoing_before(cr, uid, val, start_date_current_period, day_before_calculated_period, context=context),
            incoming_before = self._get_in_out(cr, uid, val, start_date_current_period, day_before_calculated_period, direction='in', done = False, context=context),
            stock_start = self._get_stock_start(cr, uid, val, date_for_start, context=context),
            if start_date_current_period == val.period_id.date_start:   # current period is calculated
                current=True
            else:
                current=False
            factor, round_value = self._from_default_uom_factor(cr, uid, val, val.product_uom.id, context=context)
            self.write(cr, uid, ids, {
                'already_out': rounding(already_out[0]*factor,round_value),
                'already_in': rounding(already_in[0]*factor,round_value),
                'outgoing': rounding(outgoing[0]*factor,round_value),
                'incoming': rounding(incoming[0]*factor,round_value),
                'outgoing_before' : rounding(outgoing_before[0]*factor,round_value),
                'incoming_before': rounding((incoming_before[0]+ (not current and already_in[0]))*factor,round_value),
                'outgoing_left': rounding(val.planned_outgoing - (outgoing[0] + (current and already_out[0]))*factor,round_value),
                'incoming_left': rounding(val.to_procure - (incoming[0] + (current and already_in[0]))*factor,round_value),
                'stock_start' : rounding(stock_start[0]*factor,round_value),
                'stock_simulation': rounding(val.to_procure - val.planned_outgoing + (stock_start[0]+ incoming_before[0] - outgoing_before[0] \
                                     + (not current and already_in[0]))*factor,round_value),
            })
        return True

# method below converts quantities and uoms to general OpenERP standard with UoM Qty, UoM, UoS Qty, UoS.
# from stock_planning standard where you have one Qty and one UoM (any from UoM or UoS category) 
# so if UoM is from UoM category it is used as UoM in standard and if product has UoS the UoS will be calcualated.
# If UoM is from UoS category it is recalculated to basic UoS from product (in planning you can use any UoS from UoS category) 
# and basic UoM is calculated.
    def _qty_to_standard(self, cr, uid, val, context):
        uos = False
        uos_qty = 0.0
        if val.product_uom.category_id.id == val.product_id.uom_id.category_id.id:
            uom_qty = val.incoming_left
            uom = val.product_uom.id
            if val.product_id.uos_id:
                uos = val.product_id.uos_id.id
                coeff_uom2def = self._to_default_uom_factor(cr, uid, val, val.product_uom.id, {})
                coeff_def2uom, round_value = self._from_default_uom_factor(cr, uid, val, uos, {})
                uos_qty = rounding(val.incoming_left * coeff_uom2def * coeff_def2uom, round_value)
        elif val.product_uom.category_id.id == val.product_id.uos_id.category_id.id:
            coeff_uom2def = self._to_default_uom_factor(cr, uid, val, val.product_uom.id, {})
            uos = val.product_id.uos_id.id
            coeff_def2uom, round_value = self._from_default_uom_factor(cr, uid, val, uos, {})
            uos_qty = rounding(val.incoming_left * coeff_uom2def * coeff_def2uom, round_value)
            uom = val.product_id.uom_id.id
            coeff_def2uom, round_value = self._from_default_uom_factor(cr, uid, val, uom, {})
            uom_qty = rounding(val.incoming_left * coeff_uom2def * coeff_def2uom, round_value)
        return uom_qty, uom, uos_qty, uos
    
    def procure_incomming_left(self, cr, uid, ids, context, *args):
        for obj in self.browse(cr, uid, ids):
            if obj.incoming_left <= 0:
                raise osv.except_osv(_('Error !'), _('Incoming Left must be greater than 0 !'))
            uom_qty, uom, uos_qty, uos = self._qty_to_standard(cr, uid, obj, context)
            user = self.pool.get('res.users').browse(cr, uid, uid, context)
            proc_id = self.pool.get('mrp.procurement').create(cr, uid, {
                        'company_id' : obj.company_id.id,
                        'name': _('Manual planning for ') + obj.period_id.name,
                        'origin': _('MPS(') + str(user.login) +') '+ obj.period_id.name,
                        'date_planned': obj.period_id.date_start,
                        'product_id': obj.product_id.id,
                        'product_qty': uom_qty,
                        'product_uom': uom,
                        'product_uos_qty': uos_qty,
                        'product_uos': uos,
                        'location_id': obj.procure_to_stock and obj.warehouse_id.lot_stock_id.id or obj.warehouse_id.lot_input_id.id, 
                        'procure_method': 'make_to_order',
                        'note' : _("Procurement created in MPS by user: ") + str(user.login) + _("  Creation Date: ") + \
                                            time.strftime('%Y-%m-%d %H:%M:%S') + \
                                        _("\nFor period: ") + obj.period_id.name + _(" according to state:") + \
                                        _("\n Warehouse Forecast: ") + str(obj.warehouse_forecast) + \
                                        _("\n Initial Stock: ") + str(obj.stock_start) + \
                                        _("\n Planned Out: ") + str(obj.planned_outgoing) + _("    Planned In: ") + str(obj.to_procure) + \
                                        _("\n Already Out: ") + str(obj.already_out) + _("    Already In: ") +  str(obj.already_in) + \
                                        _("\n Confirmed Out: ") + str(obj.outgoing) + _("    Confirmed In: ") + str(obj.incoming) + \
                                        _("\n Planned Out Before: ") + str(obj.outgoing_before) + _("    Confirmed In Before: ") + \
                                                                                            str(obj.incoming_before) + \
                                        _("\n Expected Out: ") + str(obj.outgoing_left) + _("    Incoming Left: ") + str(obj.incoming_left) + \
                                        _("\n Stock Simulation: ") +  str(obj.stock_simulation) + _("    Minimum stock: ") + str(obj.minimum_op),

                            }, context=context)
            wf_service = netsvc.LocalService("workflow")
            wf_service.trg_validate(uid, 'mrp.procurement', proc_id, 'button_confirm', cr)
            self.calculate_planning(cr, uid, ids, context)
            prev_text = obj.history or ""
            self.write(cr, uid, ids, {
                    'history' : prev_text + _('Requisition (') + str(user.login) + ", " + time.strftime('%Y.%m.%d %H:%M) ') + str(obj.incoming_left) + \
                    " " + obj.product_uom.name + "\n",
                })
        return True

    def internal_supply(self, cr, uid, ids, context, *args):
        for obj in self.browse(cr, uid, ids):
            if obj.incoming_left <= 0:
                raise osv.except_osv(_('Error !'), _('Incoming Left must be greater than 0 !'))
            if not obj.supply_warehouse_id:
                raise osv.except_osv(_('Error !'), _('You must specify a Source Warehouse !'))
            if obj.supply_warehouse_id.id == obj.warehouse_id.id:
                raise osv.except_osv(_('Error !'), _('You must specify a Source Warehouse different than calculated (destination) Warehouse !'))
            uom_qty, uom, uos_qty, uos = self._qty_to_standard(cr, uid, obj, context)
            user = self.pool.get('res.users').browse(cr, uid, uid, context)
            picking_id = self.pool.get('stock.picking').create(cr, uid, {
                            'origin': _('MPS(') + str(user.login) +') '+ obj.period_id.name,
                            'type': 'internal',
                            'state': 'auto',
                            'date' :  obj.period_id.date_start,
                            'move_type': 'direct',
                            'invoice_state':  'none',
                            'company_id': obj.company_id.id,
                            'note': _("Pick created from MPS by user: ") + str(user.login) + _("  Creation Date: ") + \
                                            time.strftime('%Y-%m-%d %H:%M:%S') + \
                                        _("\nFor period: ") + obj.period_id.name + _(" according to state:") + \
                                        _("\n Warehouse Forecast: ") + str(obj.warehouse_forecast) + \
                                        _("\n Initial Stock: ") + str(obj.stock_start) + \
                                        _("\n Planned Out: ") + str(obj.planned_outgoing) + _("    Planned In: ") + str(obj.to_procure) + \
                                        _("\n Already Out: ") + str(obj.already_out) + _("    Already In: ") +  str(obj.already_in) + \
                                        _("\n Confirmed Out: ") + str(obj.outgoing) + _("    Confirmed In: ") + str(obj.incoming) + \
                                        _("\n Planned Out Before: ") + str(obj.outgoing_before) + _("    Confirmed In Before: ") + \
                                                                                            str(obj.incoming_before) + \
                                        _("\n Expected Out: ") + str(obj.outgoing_left) + _("    Incoming Left: ") + str(obj.incoming_left) + \
                                        _("\n Stock Simulation: ") +  str(obj.stock_simulation) + _("    Minimum stock: ") + str(obj.minimum_op),
                        })

            move_id = self.pool.get('stock.move').create(cr, uid, {
                        'name': _('MPS(') + str(user.login) +') '+ obj.period_id.name,
                        'picking_id': picking_id,
                        'product_id': obj.product_id.id,
                        'date_planned': obj.period_id.date_start,
                        'product_qty': uom_qty,
                        'product_uom': uom,
                        'product_uos_qty': uos_qty,
                        'product_uos': uos,
                        'location_id': obj.stock_supply_location and obj.supply_warehouse_id.lot_stock_id.id or \
                                                                obj.supply_warehouse_id.lot_output_id.id,
                        'location_dest_id': obj.procure_to_stock and obj.warehouse_id.lot_stock_id.id or \
                                                                obj.warehouse_id.lot_input_id.id,
                        'tracking_id': False,
                        'company_id': obj.company_id.id,
                    })
            wf_service = netsvc.LocalService("workflow")
            wf_service.trg_validate(uid, 'stock.picking', picking_id, 'button_confirm', cr)

        self.calculate_planning(cr, uid, ids, context)
        prev_text = obj.history or ""
        pick_name = self.pool.get('stock.picking').browse(cr, uid, picking_id).name
        self.write(cr, uid, ids, {
              'history' : prev_text + _('Pick List ')+ pick_name + " (" + str(user.login) + ", " + time.strftime('%Y.%m.%d %H:%M) ') \
                + str(obj.incoming_left) +" " + obj.product_uom.name + "\n",
                })

        return True
   
    def product_id_change(self, cr, uid, ids, product_id):
        ret={}
        if product_id:
            product_rec =  self.pool.get('product.product').browse(cr, uid, product_id)
            ret['product_uom'] = product_rec.uom_id.id
            ret['active_uom'] = product_rec.uom_id.id
            ret['product_uom_categ'] = product_rec.uom_id.category_id.id
            ret['product_uos_categ'] = product_rec.uos_id and product_rec.uos_id.category_id.id or False
        else:
            ret['product_uom'] = False
            ret['product_uom_categ'] = False
            ret['product_uos_categ'] = False
        res = {'value': ret}
        return res

stock_planning()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
