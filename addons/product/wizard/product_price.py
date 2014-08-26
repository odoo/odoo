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

from openerp.osv import fields, osv


class product_price_list(osv.osv_memory):
    _name = 'product.price_list'
    _description = 'Price List'

    _columns = {
        'price_list': fields.many2one('product.pricelist', 'PriceList', required=True),
        'qty1': fields.integer('Quantity-1'),
        'qty2': fields.integer('Quantity-2'),
        'qty3': fields.integer('Quantity-3'),
        'qty4': fields.integer('Quantity-4'),
        'qty5': fields.integer('Quantity-5'),
    }
    _defaults = {
        'qty1': 1,
        'qty2': 5,
        'qty3': 10,
        'qty4': 0,
        'qty5': 0,
    }

    def print_report(self, cr, uid, ids, context=None):
        """
        To get the date and print the report
        @return : return report
        """
        if context is None:
            context = {}
        datas = {'ids': context.get('active_ids', [])}
        res = self.read(cr, uid, ids, ['price_list','qty1', 'qty2','qty3','qty4','qty5'], context=context)
        res = res and res[0] or {}
        res['price_list'] = res['price_list'][0]
        datas['form'] = res
        return self.pool['report'].get_action(cr, uid, [], 'product.report_pricelist', data=datas, context=context)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
