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
                total += line.price_unit
            result[cost.id] = total
        return result

    def _get_cost_line(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('stock.landed.cost.lines').browse(cr, uid, ids, context=context):
            result[line.cost_id.id] = True
        return result.keys()

    def onchange_pickings(self, cr, uid, ids, picking_ids=None):
        result = {'valuation_adjustment_lines': []}
        line_obj = self.pool.get('stock.valuation.adjustment.lines')
        picking_obj = self.pool.get('stock.picking')
        lines = []
 
        for cost in self.browse(cr, uid, ids):
            line_ids = [line.id for line in cost.valuation_adjustment_lines]
            line_obj.unlink(cr, uid, line_ids)

        picking_ids = picking_ids and picking_ids[0][2] or False
        if not picking_ids:
            return {'value': result}

        for picking in picking_obj.browse(cr, uid, picking_ids):
            for move in picking.move_lines:
                vals = dict(product_id = move.product_id.id, quantity = move.product_uom_qty, former_cost = move.product_uom_qty * move.price_unit)
                lines.append(vals)
        result['valuation_adjustment_lines'] = lines
        return {'value': result}

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

    def compute_landed_cost(self, cr, uid, ids, context=None):
        line_obj = self.pool.get('stock.valuation.adjustment.lines')
        for cost in self.browse(cr, uid, ids, context=None):
            total_qty = 0.0
            total_cost = 0.0
            total_line = 0.0
            for line in cost.valuation_adjustment_lines:
                total_qty += line.quantity
                total_cost += line.former_cost
                total_line += 1

        for cost in self.browse(cr, uid, ids, context=None):
            dict = {}
            for line in cost.cost_lines:
                for valuation in cost.valuation_adjustment_lines:
                    if line.split_method in ('by_quantity', 'by_weight', 'by_volume'):
                        per_unit = (line.price_unit / total_qty)
                        value = valuation.quantity * per_unit
                        if valuation.id not in dict:
                            dict.setdefault(valuation.id, value)
                        else:
                            dict[valuation.id] += value
                    elif line.split_method == 'equal':
                        per_unit = (line.price_unit / total_line)
                        if valuation.id not in dict:
                            dict.setdefault(valuation.id, per_unit)
                        else:
                            dict[valuation.id] += per_unit
                    elif line.split_method == 'by_current_cost_price':
                        per_unit = (total_cost / line.price_unit)
                        value = valuation.former_cost * per_unit
                        if valuation.id not in dict:
                            dict.setdefault(valuation.id, value)
                        else:
                            dict[valuation.id] += value

        for key, value in dict.items():
            line_obj.write(cr, uid, key, {'additional_landed_cost': value}, context=context)

        return True

class stock_landed_cost_lines(osv.osv):
    _name = 'stock.landed.cost.lines'
    _description = 'Stock Landed Cost Lines'

    def onchange_product_id(self, cr, uid, ids, product_id=False, quantity=0.0, uom_id=False, price_unit=0.0, account_id=False, context=None):
        result = {}
        if not product_id:
            return {'value': {'quantity': 0.0, 'uom_id': False, 'price_unit': 0.0}}

        product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
        result['name'] = product.name
        result['split_method'] = product.split_method
        result['price_unit'] = product.standard_price
        return {'value': result}

    _columns = {
        'name': fields.char('Description', size=256),
        'cost_id': fields.many2one('stock.landed.cost', 'Landed Cost', required=True, ondelete='cascade'),
        'product_id': fields.many2one('product.product', 'Product', required=True),
        'price_unit': fields.float('Unit Price', required=True, digits_compute= dp.get_precision('Product Price')),
        'split_method': fields.selection(product.SPLIT_METHOD, string='Split Method'),
        'account_id': fields.many2one('account.account', 'Account', domain=[('type','<>','view'), ('type', '<>', 'closed')]),
    }

class stock_valuation_adjustment_lines(osv.osv):
    _name = 'stock.valuation.adjustment.lines'
    _description = 'Stock Valuation Adjustment Lines'

    def _amount_final(self, cr, uid, ids, name, args, context=None):
        result = {}
        for line in self.browse(cr, uid, ids, context=context):
            result[line.id] = (line.former_cost + line.additional_landed_cost)
        return result

    _columns = {
        'name': fields.char('Description', size=256),
        'cost_id': fields.many2one('stock.landed.cost', 'Landed Cost', required=True, ondelete='cascade'),
        'product_id': fields.many2one('product.product', 'Product', required=True),
        'quantity': fields.float('Quantity', digits_compute= dp.get_precision('Product Unit of Measure'), required=True),
        'former_cost': fields.float('Former Cost', digits_compute= dp.get_precision('Product Price')),
        'former_cost_per_unit': fields.float('Former Cost(Per Unit)', digits_compute= dp.get_precision('Product Price')),
        'additional_landed_cost': fields.float('Additional Landed Cost', digits_compute= dp.get_precision('Product Price')),
        'final_cost': fields.function(_amount_final, string='Final Cost', type='float', digits_compute= dp.get_precision('Account'), store=True),
    }

    _defaults = {
        'quantity': 1.0,
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
