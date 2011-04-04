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
import pooler

class res_product_installer(osv.osv_memory):
    _name = 'res.product.installer'
    _inherit = 'res.config'
    _columns = {
    }
    _defaults = {
    }
    
    def execute(self, cr, uid, ids, context=None):
        if context is None:
             context = {}
        data_obj = self.pool.get('ir.model.data')
        id2 = data_obj._get_id(cr, uid, 'product', 'product_normal_form_view')
        if id2:
            id2 = data_obj.browse(cr, uid, id2, context=context).res_id
        return {
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'product.product',
                'views': [(id2, 'form')],
#                'view_id': False,
                'type': 'ir.actions.act_window',
                'target': 'new',
                'nodestroy':True,
            }

res_product_installer()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

