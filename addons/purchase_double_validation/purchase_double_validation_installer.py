# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv

class purchase_config_settings(osv.osv_memory):
    _inherit = 'purchase.config.settings'
    _columns = {
        'limit_amount': fields.integer('limit to require a second approval',required=True,
            help="Amount after which validation of purchase is required."),
    }

    _defaults = {
        'limit_amount': 5000,
    }

    def get_default_limit_amount(self, cr, uid, fields, context=None):
        ir_model_data = self.pool.get('ir.model.data')
        transition = ir_model_data.get_object(cr, uid, 'purchase_double_validation', 'trans_confirmed_double_lt')
        field, value = transition.condition.split('<', 1)
        return {'limit_amount': int(value)}

    def set_limit_amount(self, cr, uid, ids, context=None):
        ir_model_data = self.pool.get('ir.model.data')
        config = self.browse(cr, uid, ids[0], context)
        waiting = ir_model_data.get_object(cr, uid, 'purchase_double_validation', 'trans_confirmed_double_gt')
        waiting.write({'condition': 'amount_total >= %s' % config.limit_amount})
        confirm = ir_model_data.get_object(cr, uid, 'purchase_double_validation', 'trans_confirmed_double_lt')
        confirm.write({'condition': 'amount_total < %s' % config.limit_amount})
