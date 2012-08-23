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

from osv import fields, osv

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
        transition = ir_model_data.get_object(cr, uid, 'purchase_double_validation', 'trans_waiting_confirmed')
        field, value = transition.condition.split('<', 1)
        return {'limit_amount': int(value)}

    def set_limit_amount(self, cr, uid, ids, context=None):
        ir_model_data = self.pool.get('ir.model.data')
        config = self.browse(cr, uid, ids[0], context)
        waiting = ir_model_data.get_object(cr, uid, 'purchase', 'trans_confirmed_router')
        waiting.write({'condition': 'amount_total >= %s' % config.limit_amount})
        confirm = ir_model_data.get_object(cr, uid, 'purchase_double_validation', 'trans_waiting_confirmed')
        confirm.write({'condition': 'amount_total < %s' % config.limit_amount})

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
