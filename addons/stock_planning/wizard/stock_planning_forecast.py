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

# Creates forecasts records for products from selected Product Category for selected 'Warehouse - Period'
# Object added by contributor in ver 1.1
class stock_sale_forecast_createlines(osv.osv_memory):
    _name = "stock.sale.forecast.createlines"
    _description = "stock.sale.forecast.createlines"


    _columns = {
        'company_id': fields.many2one('res.company', 'Company', required=True, select=1),
        'warehouse_id': fields.many2one('stock.warehouse' , 'Warehouse', required=True, \
                                help='Warehouse which forecasts will concern. '\
                                   'If during stock planning you will need sales forecast for all warehouses choose any warehouse now.'),
        'period_id': fields.many2one('stock.period', 'Period', required=True, help='Period which forecasts will concern.'),
        'product_categ_id': fields.many2one('product.category' , 'Product Category', required=True, \
                                help ='Product Category of products which created forecasts will concern.'),
        'copy_forecast': fields.boolean('Copy Last Forecast', help="Copy quantities from last Stock and Sale Forecast."),
    }

    _defaults = {
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'stock.sale.forecast.createlines', context=c),
    }

    def create_forecast(self, cr, uid, ids, context=None):
        product_obj = self.pool.get('product.product')
        forecast_obj = self.pool.get('stock.sale.forecast')
        mod_obj = self.pool.get('ir.model.data')
        prod_categ_obj = self.pool.get('product.category')
        template_obj = self.pool.get('product.template')
        forecast_lines = []
        for f in self.browse(cr, uid, ids, context=context):
            categ_ids =  f.product_categ_id.id and [f.product_categ_id.id] or []
            prod_categ_ids = prod_categ_obj.search(cr, uid, [('parent_id','child_of', categ_ids)])
            templates_ids = template_obj.search(cr, uid, [('categ_id','in',prod_categ_ids)])
            products_ids = product_obj.search(cr, uid, [('product_tmpl_id','in',templates_ids)])
            if len(products_ids) == 0:
                raise osv.except_osv(_('Error !'), _('No products in selected category !'))
            copy = f.copy_forecast
            for p in product_obj.browse(cr, uid, products_ids,{}):
                if len(forecast_obj.search(cr, uid, [('product_id','=',p.id) , \
                                                       ('period_id','=',f.period_id.id), \
                                                       ('user_id','=',uid), \
                                                       ('warehouse_id','=',f.warehouse_id.id)]))== 0:
                    forecast_qty = 0.0
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
                                    (uid, uid, uid, f.warehouse_id.id, p.id, f.period_id.date_stop) )
                        ret = cr.fetchone()
                        if ret:
                            forecast_qty = ret[1]
                            prod_uom = ret[2]
                    prod_uom = prod_uom or p.uom_id.id
                    prod_uos_categ = False
                    if p.uos_id:
                        prod_uos_categ = p.uos_id.category_id.id
                    forecast_lines.append(forecast_obj.create(cr, uid, {
                        'company_id': f.warehouse_id.company_id.id,
                        'period_id': f.period_id.id,
                        'warehouse_id': f.warehouse_id.id,
                        'product_id': p.id,
                        'product_qty': forecast_qty,
                        'product_amt': 0.0,
                        'product_uom': prod_uom,
                        'active_uom': prod_uom,
                        'product_uom_categ': p.uom_id.category_id.id,
                        'product_uos_categ': prod_uos_categ,
                     }))

        return {
            'domain': "[('id','in', ["+','.join(map(str, forecast_lines))+"])]",
            'view_type': 'form',
            "view_mode": 'tree,form',
            'res_model': 'stock.sale.forecast',
            'type': 'ir.actions.act_window',
        }

stock_sale_forecast_createlines()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
