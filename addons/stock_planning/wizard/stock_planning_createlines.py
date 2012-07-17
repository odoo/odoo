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

from osv import osv, fields
from tools.translate import _

# Creates stock planning records for products from selected Product Category for selected 'Warehouse - Period'
# Object added by contributor in ver 1.1
class stock_planning_createlines(osv.osv_memory):
    _name = "stock.planning.createlines"

    def onchange_company(self, cr, uid, ids, company_id=False):
        result = {}
        if company_id:
            result['warehouse_id'] = False
        return {'value': result}

    _columns = {
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'period_id': fields.many2one('stock.period' , 'Period', required=True, help = 'Period which planning will concern.'),
        'warehouse_id': fields.many2one('stock.warehouse' , 'Warehouse', required=True, help = 'Warehouse which planning will concern.'),
        'product_categ_id': fields.many2one('product.category' , 'Product Category', \
                        help = 'Planning will be created for products from Product Category selected by this field. '\
                               'This field is ignored when you check \"All Forecasted Product\" box.' ),
        'forecasted_products': fields.boolean('All Products with Forecast', \
                     help = "Check this box to create planning for all products having any forecast for selected Warehouse and Period. "\
                            "Product Category field will be ignored."),
    }

    _defaults = {
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'stock.planning', context=c),
    }

    def create_planning(self,cr, uid, ids, context=None):
        if context is None:
            context = {}
        product_obj = self.pool.get('product.product')
        planning_obj = self.pool.get('stock.planning')
        mod_obj = self.pool.get('ir.model.data')
        prod_categ_obj = self.pool.get('product.category')
        planning_lines = []
        for f in self.browse(cr, uid, ids, context=context):
            if f.forecasted_products:
                cr.execute("SELECT product_id \
                                FROM stock_sale_forecast \
                                WHERE (period_id = %s) AND (warehouse_id = %s)", (f.period_id.id, f.warehouse_id.id))
                products_id1 = [x for x, in cr.fetchall()]
            else:
                categ_ids = f.product_categ_id.id and [f.product_categ_id.id] or []
                prod_categ_ids = prod_categ_obj.search(cr,uid,[('parent_id','child_of',categ_ids)])
                products_id1 = product_obj.search(cr,uid,[('categ_id','in',prod_categ_ids)])
            if len(products_id1)==0:
                raise osv.except_osv(_('Error !'), _('No forecasts for selected period or no products available in selected category !'))

            for p in product_obj.browse(cr, uid, products_id1,context=context):
                if len(planning_obj.search(cr, uid, [('product_id','=',p.id),
                                                      ('period_id','=',f.period_id.id),
                                                      ('warehouse_id','=',f.warehouse_id.id)]))== 0:
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
                                    (uid, uid, f.warehouse_id.id, p.id, f.period_id.date_stop) )
                    ret=cr.fetchone()
                    if ret:
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
                    planning_lines.append(planning_obj.create(cr, uid, {
                        'company_id' : f.warehouse_id.company_id.id,
                        'period_id': f.period_id.id,
                        'warehouse_id' : f.warehouse_id.id,
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

                    }))

        return {
            'domain': "[('id','in', ["+','.join(map(str, planning_lines))+"])]",
            'view_type': 'form',
            "view_mode": 'tree,form',
            'res_model': 'stock.planning',
            'type': 'ir.actions.act_window',
        }

stock_planning_createlines()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
