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

from osv import osv, fields
from tools.translate import _
  

class product_price_list(osv.osv_memory):
    _name = 'product.price_list'
    _description = 'Product Price List'

    _columns = {
        'price_list': fields.many2one('product.pricelist', 'PriceList', required=True),
        'qty1': fields.integer('Quantity-1'),
        'qty2': fields.integer('Quantity-2'),
        'qty3': fields.integer('Quantity-3'),
        'qty4': fields.integer('Quantity-4'),
        'qty5': fields.integer('Quantity-5'),
    }
    _defaults = {
        'qty1': lambda *a: 0,
        'qty2': lambda *a: 0,
        'qty3': lambda *a: 0,
        'qty4': lambda *a: 0,
        'qty5': lambda *a: 0,
    }

    def print_report(self, cr, uid, ids, context=None):

        """
              To get the date and print the report
             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param context: A standard dictionary
             @return : return report
        """
        datas = {'ids': context.get('active_ids', [])}
        res = self.read(cr, uid, ids, ['price_list','qty1', 'qty2','qty3','qty4','qty5'], context)
        res = res and res[0] or {}
        datas['form'] = res
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'product.pricelist',
            'datas': datas,
       }
product_price_list()        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

