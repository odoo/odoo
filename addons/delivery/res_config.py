# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (C) 2004-2012 OpenERP S.A. (<http://openerp.com>).
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

class delivery_configuration(osv.osv_memory):
    _inherit = 'stock.config.settings'
    _columns = {
        'decimal_precision_stock': fields.integer('Decimal Precision on Stock Weight'),
    }

    def get_default_dp(self, cr, uid, fields, context=None):
        stock_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'product', 'decimal_stock_weight')[1]
        dec_id =self.pool.get('decimal.precision').browse(cr, uid, stock_id, context=context)
        return {
            'decimal_precision_stock': dec_id.digits,
        }
        
    def set_default_dp(self, cr, uid, ids, context=None):
        config = self.browse(cr, uid, ids[0], context)
        stock_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'product', 'decimal_stock_weight')[1]
        dec_id =self.pool.get('decimal.precision').browse(cr, uid, stock_id, context=context) 
        dec_id.write({
            'digits': config.decimal_precision_stock,
        })     

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
