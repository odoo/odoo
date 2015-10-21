# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.exceptions import UserError
from openerp.osv import fields, osv
from openerp.tools.translate import _

class wizard_price(osv.osv):
    _name = "wizard.price"
    _description = "Compute Price Wizard"
    _columns = {
        'info_field': fields.text('Info', readonly=True), 
        'real_time_accounting': fields.boolean("Generate accounting entries when real-time"),
        'recursive': fields.boolean("Change prices of child BoMs too"),
        }

    def default_get(self, cr, uid, fields, context=None):
        res = super(wizard_price, self).default_get(cr, uid, fields, context=context)
        product_pool = self.pool.get('product.template')
        product_obj = product_pool.browse(cr, uid, context.get('active_id', False))
        if context is None:
            context = {}
        rec_id = context and context.get('active_id', False)
        assert rec_id, _('Active ID is not set in Context.')
        computed_price = product_pool.compute_price(cr, uid, [], template_ids=[product_obj.id], test=True, context=context)
        if product_obj.id in computed_price:
            res['info_field'] = "%s: %s" % (product_obj.name, computed_price[product_obj.id]) 
        else:
            res['info_field'] = ""
        return res

    def compute_from_bom(self, cr, uid, ids, context=None):
        assert len(ids) == 1
        if context is None:
            context = {}
        model = context.get('active_model')
        if model != 'product.template':
            raise UserError(_('This wizard is built for product templates, while you are currently running it from a product variant.'))
        rec_id = context and context.get('active_id', False)
        assert rec_id, _('Active ID is not set in Context.')
        prod_obj = self.pool.get('product.template')
        res = self.browse(cr, uid, ids, context=context)
        prod = prod_obj.browse(cr, uid, rec_id, context=context)
        prod_obj.compute_price(cr, uid, [], template_ids=[prod.id], real_time_accounting=res[0].real_time_accounting, recursive=res[0].recursive, test=False, context=context)
