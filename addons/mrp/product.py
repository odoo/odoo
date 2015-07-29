# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv


class product_template(osv.osv):
    _inherit = "product.template"
    def _bom_orders_count(self, cr, uid, ids, field_name, arg, context=None):
        Bom = self.pool('mrp.bom')
        res = {}
        for product_tmpl_id in ids:
            nb = Bom.search_count(cr, uid, [('product_tmpl_id', '=', product_tmpl_id)], context=context)
            res[product_tmpl_id] = {
                'bom_count': nb,
            }
        return res

    def _bom_orders_count_mo(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for product_tmpl_id in self.browse(cr, uid, ids):
            res[product_tmpl_id.id] = sum([p.mo_count for p in product_tmpl_id.product_variant_ids])
        return res

    _columns = {
        'bom_ids': fields.one2many('mrp.bom', 'product_tmpl_id','Bill of Materials'),
        'bom_count': fields.function(_bom_orders_count, string='# Bill of Material', type='integer', multi="_bom_order_count"),
        'mo_count': fields.function(_bom_orders_count_mo, string='# Manufacturing Orders', type='integer'),
        'produce_delay': fields.float('Manufacturing Lead Time', help="Average delay in days to produce this product. In the case of multi-level BOM, the manufacturing lead times of the components will be added."),
    }

    _defaults = {
        'produce_delay': 1,
    }
    
    
    def action_view_mos(self, cr, uid, ids, context=None):
        products = self._get_products(cr, uid, ids, context=context)
        result = self._get_act_window_dict(cr, uid, 'mrp.act_product_mrp_production', context=context)
        if len(ids) == 1 and len(products) == 1:
            result['context'] = "{'default_product_id': " + str(products[0]) + ", 'search_default_product_id': " + str(products[0]) + "}"
        else:
            result['domain'] = "[('product_id','in',[" + ','.join(map(str, products)) + "])]"
            result['context'] = "{}"
        return result


class product_product(osv.osv):
    _inherit = "product.product"
    def _bom_orders_count(self, cr, uid, ids, field_name, arg, context=None):
        Production = self.pool('mrp.production')
        res = {}
        for product_id in ids:
            res[product_id] = Production.search_count(cr,uid, [('product_id', '=', product_id)], context=context)
        return res

    _columns = {
        'mo_count': fields.function(_bom_orders_count, string='# Manufacturing Orders', type='integer'),
    }

    def action_view_bom(self, cr, uid, ids, context=None):
        result = self.pool.get("product.template")._get_act_window_dict(cr, uid, 'mrp.product_open_bom', context=context)
        templates = [product.product_tmpl_id.id for product in self.browse(cr, uid, ids, context=context)]
        # bom specific to this variant or global to template
        context = {
            'search_default_product_tmpl_id': templates[0],
            'search_default_product_id': ids[0],
            'default_product_tmpl_id': templates[0],
            'default_product_id': ids[0],
        }
        result['context'] = str(context)
        return result
