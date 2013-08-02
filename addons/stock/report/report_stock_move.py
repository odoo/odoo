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

from openerp import tools
from openerp.osv import fields,osv
from openerp.addons.decimal_precision import decimal_precision as dp

# FP Note: TODO: move in stock.py
class stock_quant(osv.osv):
    _inherit = "stock.quant"
    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False):
        res = super(stock_quant, self).read_group(cr, uid, domain, fields, groupby, offset=offset, limit=limit, context=context, orderby=orderby)
        product_obj = self.pool.get("product.product")
        if 'inventory_value' in fields:
            for line in res:
                if '__domain' in line:
                    lines = self.search(cr, uid, line['__domain'], context=context)
                    inv_value = 0.0
                    for line2 in self.browse(cr, uid, lines, context=context):
                        inv_value += line2.inventory_value
                    line['inventory_value'] = inv_value
        return res
    
    def _calc_moves(self, cr, uid, ids, name, attr, context=None):
        product_obj = self.pool.get("product.product")
        res = {}
        proddict = {}
        # Fill proddict with the products we will need browse records from (optimization)
        lines = self.browse(cr, uid, ids, context=context)
        for line in lines:
            if not line.company_id.id in proddict:
                proddict[line.company_id.id] = {}
            proddict[line.company_id.id][line.product_id.id] = True
        prodbrow = {}
        # Fill prodbrow with browse records needed from proddict
        for prodelem in proddict.keys():
            ctx = context.copy()
            ctx['force_company'] = prodelem
            prods = product_obj.browse(cr, uid, proddict[prodelem].keys(), context=ctx)
            for prod in prods:
                prodbrow[(prodelem, prod.id)] = prod
        # use prodbrow and existing value on quants to calculate the inventory_value on the report lines
        for line in lines:
            ctx = context.copy()
            ctx['force_company'] = line.company_id.id
            prod = product_obj.browse(cr, uid, line.product_id.id, context=ctx)
            res[line.id] = self._get_inventory_value(cr, uid, line, prodbrow, context=ctx)
        return res

    def _get_inventory_value(self, cr, uid, line, prodbrow, context=None):
        return prodbrow[(line.company_id.id, line.product_id.id)].standard_price * line.qty

    _columns = {
        'inventory_value': fields.function(_calc_moves, string="Inventory Value", type='float', readonly=True), 
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
