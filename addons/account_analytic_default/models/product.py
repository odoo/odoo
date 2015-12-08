# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv


class product_product(osv.Model):
    _inherit = 'product.product'

    def _rules_count(self, cr, uid, ids, field_name, arg, context=None):
        Analytic = self.pool['account.analytic.default']
        return {
            product_id: Analytic.search_count(cr, uid, [('product_id', '=', product_id)], context=context)
            for product_id in ids
        }
    _columns = {
        'rules_count': fields.function(_rules_count, string='# Analytic Rules', type='integer'),
    }


class product_template(osv.Model):
    _inherit = 'product.template'

    def _rules_count(self, cr, uid, ids, field_name, arg, context=None):
        Analytic = self.pool['account.analytic.default']
        res = {}
        for product_tmpl_id in self.browse(cr, uid, ids, context=context):
            res[product_tmpl_id.id] = sum([p.rules_count for p in product_tmpl_id.product_variant_ids])
        return res

    _columns = {
        'rules_count': fields.function(_rules_count, string='# Analytic Rules', type='integer'),
    }


    def action_view_rules(self, cr, uid, ids, context=None):
        products = self._get_products(cr, uid, ids, context=context)
        result = self._get_act_window_dict(cr, uid, 'account_analytic_default.action_product_default_list', context=context)
        result['domain'] = "[('product_id','in',[" + ','.join(map(str, products)) + "])]"
        # Remove context so it is not going to filter on product_id with active_id of template
        result['context'] = "{}"
        return result
