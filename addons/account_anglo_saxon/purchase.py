# -*- encoding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

from openerp.osv import fields, osv

class purchase_order(osv.osv):
    _name = "purchase.order"
    _inherit = "purchase.order"
    _description = "Purchase Order"

    def _prepare_inv_line(self, cr, uid, account_id, order_line, context=None):
        line = super(purchase_order, self)._prepare_inv_line(cr, uid, account_id, order_line, context=context)
        if order_line.product_id and not order_line.product_id.type == 'service':
            acc_id = order_line.product_id.property_stock_account_input and order_line.product_id.property_stock_account_input.id
            if not acc_id:
                acc_id = order_line.product_id.categ_id.property_stock_account_input_categ and order_line.product_id.categ_id.property_stock_account_input_categ.id
            if acc_id:
                fpos = order_line.order_id.fiscal_position or False
                new_account_id = self.pool.get('account.fiscal.position').map_account(cr, uid, fpos, acc_id)
                line.update({'account_id': new_account_id})
        return line
purchase_order()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
