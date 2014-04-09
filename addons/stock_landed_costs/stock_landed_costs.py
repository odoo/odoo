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

import time

from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp
import product

class stock_landed_cost(osv.osv):
    _name = 'stock.landed.cost'
    _description = 'Stock Landed Cost'

    def _total_amount(self, cr, uid, ids, name, args, context=None):
        result = {}
        for cost in self.browse(cr, uid, ids, context=context):
            total = 0.0
            for line in cost.cost_lines:
                total += line.price_subtotal
            result[cost.id] = total
        return result

    def _get_cost_line(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('stock.landed.cost.lines').browse(cr, uid, ids, context=context):
            result[line.cost_id.id] = True
        return result.keys()

    _columns = {
        'name': fields.char('Name', size=256, required=True),
        'date': fields.datetime('Date', required=True),
        'picking_ids': fields.many2many('stock.picking', string='Pickings'),
        'cost_lines': fields.one2many('stock.landed.cost.lines', 'cost_id', 'Cost Lines'),
        'valuation_adjustment_lines': fields.one2many('stock.valuation.adjustment.lines', 'cost_id', 'Valuation Adjustments'),
        'description': fields.text('Item Description'),
        'amount_total': fields.function(_total_amount, type='float', string='Total', digits_compute=dp.get_precision('Account'),
            store={
                'stock.landed.cost': (lambda self, cr, uid, ids, c={}: ids, ['cost_lines'], 20),
                'stock.landed.cost.lines': (_get_cost_line, ['price_unit', 'quantity', 'cost_id'], 20),
            }
        ),
        'state':fields.selection([('draft', 'Draft'), ('open', 'Open'), ('cancel', 'Cancelled')], 'State', readonly=True),
    }

    _defaults = {
        'state': 'draft',
        'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
    }

    def button_validate(self, cr ,uid, ids, context=None):
        return True

    def button_cancel(self, cr ,uid, ids, context=None):
        return True

class stock_landed_cost_lines(osv.osv):
    _name = 'stock.landed.cost.lines'
    _description = 'Stock Landed Cost Lines'

    def _amount_subtotal(self, cr, uid, ids, name, args, context=None):
        result = {}
        for line in self.browse(cr, uid, ids, context=context):
            result[line.id] = (line.quantity * line.price_unit)
        return result

    def onchange_product_id(self, cr, uid, ids, product_id=False, quantity=0.0, uom_id=False, price_unit=0.0, account_id=False, context=None):
        result = {}
        if not product_id:
            return {'value': {'quantity': 0.0, 'uom_id': False, 'price_unit': 0.0}}

        product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
        result['name'] = product.name
        result['split_method'] = product.split_method
        result['price_unit'] = product.standard_price
        result['uom_id'] = product.uom_id.id
        return {'value': result}

    _columns = {
        'name': fields.char('Description', size=256),
        'cost_id': fields.many2one('stock.landed.cost', 'Landed Cost', required=True, ondelete='cascade'),
        'product_id': fields.many2one('product.product', 'Product', required=True),
        'uom_id': fields.many2one('product.uom', 'Unit of Measure', ondelete='set null', select=True),
        'quantity': fields.float('Quantity', digits_compute= dp.get_precision('Product Unit of Measure'), required=True),
        'price_unit': fields.float('Unit Price', required=True, digits_compute= dp.get_precision('Product Price')),
        'split_method': fields.selection(product.SPLIT_METHOD, string='Split Method'),
        'account_id': fields.many2one('account.account', 'Account', domain=[('type','<>','view'), ('type', '<>', 'closed')]),
        'price_subtotal': fields.function(_amount_subtotal, string='Amount', type='float', digits_compute= dp.get_precision('Account'), store=True),
    }

    _defaults = {
        'quantity': 1.0,
        'split_method': 'equal',
    }

class stock_valuation_adjustment_lines(osv.osv):
    _name = 'stock.valuation.adjustment.lines'
    _description = 'Stock Valuation Adjustment Lines'

    _columns = {
        'name': fields.char('Description', size=256),
        'cost_id': fields.many2one('stock.landed.cost', 'Landed Cost', required=True, ondelete='cascade'),
        'product_id': fields.many2one('product.product', 'Product', required=True),
        'quantity': fields.float('Quantity', digits_compute= dp.get_precision('Product Unit of Measure'), required=True),
        'former_cost': fields.float('Former Cost', required=True, digits_compute= dp.get_precision('Product Price')),
        'former_cost_per_unit': fields.float('Former Cost(Per Unit)', required=True, digits_compute= dp.get_precision('Product Price')),
        'additional_landed_cost': fields.float('Additional Landed Cost', required=True, digits_compute= dp.get_precision('Product Price')),
        'final_cost': fields.float('Final Cost', required=True, digits_compute= dp.get_precision('Product Price')),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
