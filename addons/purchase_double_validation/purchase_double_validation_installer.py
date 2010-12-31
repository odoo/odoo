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

class purchase_double_validation_installer(osv.osv_memory):
    _name = 'purchase.double.validation.installer'
    _inherit = 'res.config'
    _columns = {
        'limit_amount': fields.integer('Maximum Purchase Amount', required=True, help="Maximum amount after which validation of purchase is required."),
    }

    _defaults = {
        'limit_amount': 5000,
    }

    def execute(self, cr, uid, ids, context=None):
        data = self.read(cr, uid, ids, context=context)
        if not data:
            return {}
        amt = data[0]['limit_amount']
        data_pool = self.pool.get('ir.model.data')
        transition_obj = self.pool.get('workflow.transition')
        waiting = data_pool._get_id(cr, uid, 'purchase', 'trans_confirmed_router')
        waiting_id = data_pool.browse(cr, uid, waiting, context=context).res_id
        confirm = data_pool._get_id(cr, uid, 'purchase_double_validation', 'trans_waiting_confirmed')
        confirm_id = data_pool.browse(cr, uid, confirm, context=context).res_id
        transition_obj.write(cr, uid, waiting_id, {'condition': 'amount_total>=%s' % (amt)})
        transition_obj.write(cr, uid, confirm_id, {'condition': 'amount_total<%s' % (amt)})
        return {}

purchase_double_validation_installer()



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

