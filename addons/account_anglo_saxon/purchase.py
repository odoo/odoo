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

from osv import fields, osv

class purchase_order(osv.osv):
    _name = "purchase.order"
    _inherit = "purchase.order"
    _description = "Purchase Order"

    def inv_line_create(self, cr, uid, a, ol):
        line = super(purchase_order, self).inv_line_create(cr, uid, a, ol)
        if ol.product_id:
            oa = ol.product_id.property_stock_account_input and ol.product_id.property_stock_account_input.id
            if not oa:
                oa = ol.product_id.categ_id.property_stock_account_input_categ and ol.product_id.categ_id.property_stock_account_input_categ.id
            if oa:
                fpos = ol.order_id.fiscal_position or False
                a = self.pool.get('account.fiscal.position').map_account(cr, uid, fpos, oa)
                line[2].update({'account_id': a})
        return line
purchase_order()
