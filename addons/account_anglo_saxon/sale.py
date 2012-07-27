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

#class sale_order_line(osv.osv):
#    _name = 'sale.order.line'
#    _description = 'Sale Order line'
#    _inherit = 'sale.order.line'
#
#    def invoice_line_create(self, cr, uid, ids, context={}):
#        line_ids = super('sale_order_line',self).invoice_line_create(cr, uid, ids, context)
#        invoice_line_obj = self.pool.get('account.invoice.line')
#        for line in invoice_line_obj.browse(cr, uid, line_ids):
#            if line.product_id:
#                    a =  line.product_id.property_stock_account_output and line.product_id.property_stock_account_output.id
#                    if not a:
#                        a = line.product_id.categ_id.property_stock_account_output_categ and line.product_id.categ_id.property_stock_account_output_categ.id
#                    if a:
#                        a = self.pool.get('account.fiscal.position').map_account(cr, uid, fpos, a)
#                        invoice_line_obj.write(cr, uid, line.id, {'account_id':a})
#
#sale_order_line()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
