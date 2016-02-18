# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp
from openerp.tools import float_compare, float_round
from openerp.tools.translate import _
import product
from openerp import SUPERUSER_ID
from openerp.exceptions import UserError


class stock_landed_cost(osv.osv):
    _name = 'stock.landed.cost'
    _description = 'Stock Landed Cost'
    _inherit = 'mail.thread'

    def _total_amount(self, cr, uid, ids, name, args, context=None):
        result = {}
        for cost in self.browse(cr, uid, ids, context=context):
            total = 0.0
            for line in cost.cost_lines:
                total += line.price_unit
            result[cost.id] = total
        return result

    def _get_cost_line(self, cr, uid, ids, context=None):
        cost_to_recompute = []
        for line in self.pool.get('stock.landed.cost.lines').browse(cr, uid, ids, context=context):
            cost_to_recompute.append(line.cost_id.id)
        return cost_to_recompute

    def get_valuation_lines(self, cr, uid, ids, picking_ids=None, context=None):
        picking_obj = self.pool.get('stock.picking')
        lines = []
        if not picking_ids:
            return lines

        for picking in picking_obj.browse(cr, uid, picking_ids):
            for move in picking.move_lines:
                #it doesn't make sense to make a landed cost for a product that isn't set as being valuated in real time at real cost
                if move.product_id.valuation != 'real_time' or move.product_id.cost_method != 'real':
                    continue
                total_cost = 0.0
                weight = move.product_id and move.product_id.weight * move.product_qty
                volume = move.product_id and move.product_id.volume * move.product_qty
                for quant in move.quant_ids:
                    total_cost += quant.cost * quant.qty
                vals = dict(product_id=move.product_id.id, move_id=move.id, quantity=move.product_qty, former_cost=total_cost, weight=weight, volume=volume)
                lines.append(vals)
        if not lines:
            raise UserError(_('The selected picking does not contain any move that would be impacted by landed costs. Landed costs are only possible for products configured in real time valuation with real price costing method. Please make sure it is the case, or you selected the correct picking'))
        return lines

    _columns = {
        'name': fields.char('Name', track_visibility='always', readonly=True, copy=False),
        'date': fields.date('Date', required=True, states={'done': [('readonly', True)]}, track_visibility='onchange', copy=False),
        'picking_ids': fields.many2many('stock.picking', string='Pickings', states={'done': [('readonly', True)]}, copy=False),
        'cost_lines': fields.one2many('stock.landed.cost.lines', 'cost_id', 'Cost Lines', states={'done': [('readonly', True)]}, copy=True),
        'valuation_adjustment_lines': fields.one2many('stock.valuation.adjustment.lines', 'cost_id', 'Valuation Adjustments', states={'done': [('readonly', True)]}),
        'description': fields.text('Item Description', states={'done': [('readonly', True)]}),
        'amount_total': fields.function(_total_amount, type='float', string='Total', digits=0,
            store={
                'stock.landed.cost': (lambda self, cr, uid, ids, c={}: ids, ['cost_lines'], 20),
                'stock.landed.cost.lines': (_get_cost_line, ['price_unit', 'quantity', 'cost_id'], 20),
            }, track_visibility='always'
        ),
        'state': fields.selection([('draft', 'Draft'), ('done', 'Posted'), ('cancel', 'Cancelled')], 'State', readonly=True, track_visibility='onchange', copy=False),
        'account_move_id': fields.many2one('account.move', 'Journal Entry', readonly=True, copy=False),
        'account_journal_id': fields.many2one('account.journal', 'Account Journal', required=True, states={'done': [('readonly', True)]}),
    }

    _defaults = {
        'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').next_by_code(cr, uid, 'stock.landed.cost'),
        'state': 'draft',
        'date': fields.date.context_today,
    }

    def _create_accounting_entries(self, cr, uid, line, move_id, qty_out, context=None):
        product_obj = self.pool.get('product.template')
        cost_product = line.cost_line_id and line.cost_line_id.product_id
        if not cost_product:
            return False
        accounts = product_obj.browse(cr, uid, line.product_id.product_tmpl_id.id, context=context).get_product_accounts()
        debit_account_id = accounts.get('stock_valuation', False) and accounts['stock_valuation'].id or False
        already_out_account_id = accounts['stock_output'].id
        credit_account_id = line.cost_line_id.account_id.id or cost_product.property_account_expense_id.id or cost_product.categ_id.property_account_expense_categ_id.id

        if not credit_account_id:
            raise UserError(_('Please configure Stock Expense Account for product: %s.') % (cost_product.name))

        return self._create_account_move_line(cr, uid, line, move_id, credit_account_id, debit_account_id, qty_out, already_out_account_id, context=context)

    def _create_account_move_line(self, cr, uid, line, move_id, credit_account_id, debit_account_id, qty_out, already_out_account_id, context=None):
        """
        Generate the account.move.line values to track the landed cost.
        Afterwards, for the goods that are already out of stock, we should create the out moves
        """
        aml_obj = self.pool.get('account.move.line')
        if context is None:
            context = {}
        ctx = context.copy()
        ctx['check_move_validity'] = False
        base_line = {
            'name': line.name,
            'move_id': move_id,
            'product_id': line.product_id.id,
            'quantity': line.quantity,
        }
        debit_line = dict(base_line, account_id=debit_account_id)
        credit_line = dict(base_line, account_id=credit_account_id)
        diff = line.additional_landed_cost
        if diff > 0:
            debit_line['debit'] = diff
            credit_line['credit'] = diff
        else:
            # negative cost, reverse the entry
            debit_line['credit'] = -diff
            credit_line['debit'] = -diff
        aml_obj.create(cr, uid, debit_line, context=ctx)
        aml_obj.create(cr, uid, credit_line, context=ctx)
        
        #Create account move lines for quants already out of stock
        if qty_out > 0:
            debit_line = dict(debit_line,
                              name=(line.name + ": " + str(qty_out) + _(' already out')),
                              quantity=qty_out,
                              account_id=already_out_account_id)
            credit_line = dict(credit_line,
                              name=(line.name + ": " + str(qty_out) + _(' already out')),
                              quantity=qty_out,
                              account_id=debit_account_id)
            diff = diff * qty_out / line.quantity
            if diff > 0:
                debit_line['debit'] = diff
                credit_line['credit'] = diff
            else:
                # negative cost, reverse the entry
                debit_line['credit'] = -diff
                credit_line['debit'] = -diff
            aml_obj.create(cr, uid, debit_line, context=ctx)
            aml_obj.create(cr, uid, credit_line, context=ctx)
        self.pool.get('account.move').assert_balanced(cr, uid, [move_id], context=context)
        return True

    def _create_account_move(self, cr, uid, cost, context=None):
        vals = {
            'journal_id': cost.account_journal_id.id,
            'date': cost.date,
            'ref': cost.name
        }
        return self.pool.get('account.move').create(cr, uid, vals, context=context)

    def _check_sum(self, cr, uid, landed_cost, context=None):
        """
        Will check if each cost line its valuation lines sum to the correct amount
        and if the overall total amount is correct also
        """
        costcor = {}
        tot = 0
        for valuation_line in landed_cost.valuation_adjustment_lines:
            if costcor.get(valuation_line.cost_line_id):
                costcor[valuation_line.cost_line_id] += valuation_line.additional_landed_cost
            else:
                costcor[valuation_line.cost_line_id] = valuation_line.additional_landed_cost
            tot += valuation_line.additional_landed_cost

        prec = self.pool['decimal.precision'].precision_get(cr, uid, 'Account')
        # float_compare returns 0 for equal amounts
        res = not bool(float_compare(tot, landed_cost.amount_total, precision_digits=prec))
        for costl in costcor.keys():
            if float_compare(costcor[costl], costl.price_unit, precision_digits=prec):
                res = False
        return res

    def button_validate(self, cr, uid, ids, context=None):
        quant_obj = self.pool.get('stock.quant')

        for cost in self.browse(cr, uid, ids, context=context):
            if cost.state != 'draft':
                raise UserError(_('Only draft landed costs can be validated'))
            if not cost.valuation_adjustment_lines or not self._check_sum(cr, uid, cost, context=context):
                raise UserError(_('You cannot validate a landed cost which has no valid valuation adjustments lines. Did you click on Compute?'))
            move_id = self._create_account_move(cr, uid, cost, context=context)
            for line in cost.valuation_adjustment_lines:
                if not line.move_id:
                    continue
                per_unit = line.final_cost / line.quantity
                diff = per_unit - line.former_cost_per_unit
                quants = [quant for quant in line.move_id.quant_ids]
                quant_dict = {}
                for quant in quants:
                    if quant.id not in quant_dict:
                        quant_dict[quant.id] = quant.cost + diff
                    else:
                        quant_dict[quant.id] += diff
                for key, value in quant_dict.items():
                    quant_obj.write(cr, SUPERUSER_ID, key, {'cost': value}, context=context)
                qty_out = 0
                for quant in line.move_id.quant_ids:
                    if quant.location_id.usage != 'internal':
                        qty_out += quant.qty
                self._create_accounting_entries(cr, uid, line, move_id, qty_out, context=context)
            self.write(cr, uid, cost.id, {'state': 'done', 'account_move_id': move_id}, context=context)
            self.pool.get('account.move').post(cr, uid, [move_id], context=context)
        return True

    def button_cancel(self, cr, uid, ids, context=None):
        cost = self.browse(cr, uid, ids, context=context)
        if cost.state == 'done':
            raise UserError(_('Validated landed costs cannot be cancelled, '
                            'but you could create negative landed costs to reverse them'))
        return cost.write({'state': 'cancel'})

    def unlink(self, cr, uid, ids, context=None):
        # cancel or raise first
        self.button_cancel(cr, uid, ids, context)
        return super(stock_landed_cost, self).unlink(cr, uid, ids, context=context)

    def compute_landed_cost(self, cr, uid, ids, context=None):
        line_obj = self.pool.get('stock.valuation.adjustment.lines')
        unlink_ids = line_obj.search(cr, uid, [('cost_id', 'in', ids)], context=context)
        line_obj.unlink(cr, uid, unlink_ids, context=context)
        digits = dp.get_precision('Product Price')(cr)
        towrite_dict = {}
        for cost in self.browse(cr, uid, ids, context=None):
            if not cost.picking_ids:
                continue
            picking_ids = [p.id for p in cost.picking_ids]
            total_qty = 0.0
            total_cost = 0.0
            total_weight = 0.0
            total_volume = 0.0
            total_line = 0.0
            vals = self.get_valuation_lines(cr, uid, [cost.id], picking_ids=picking_ids, context=context)
            for v in vals:
                for line in cost.cost_lines:
                    v.update({'cost_id': cost.id, 'cost_line_id': line.id})
                    self.pool.get('stock.valuation.adjustment.lines').create(cr, uid, v, context=context)
                total_qty += v.get('quantity', 0.0)
                total_cost += v.get('former_cost', 0.0)
                total_weight += v.get('weight', 0.0)
                total_volume += v.get('volume', 0.0)
                total_line += 1

            for line in cost.cost_lines:
                value_split = 0.0
                for valuation in cost.valuation_adjustment_lines:
                    value = 0.0
                    if valuation.cost_line_id and valuation.cost_line_id.id == line.id:
                        if line.split_method == 'by_quantity' and total_qty:
                            per_unit = (line.price_unit / total_qty)
                            value = valuation.quantity * per_unit
                        elif line.split_method == 'by_weight' and total_weight:
                            per_unit = (line.price_unit / total_weight)
                            value = valuation.weight * per_unit
                        elif line.split_method == 'by_volume' and total_volume:
                            per_unit = (line.price_unit / total_volume)
                            value = valuation.volume * per_unit
                        elif line.split_method == 'equal':
                            value = (line.price_unit / total_line)
                        elif line.split_method == 'by_current_cost_price' and total_cost:
                            per_unit = (line.price_unit / total_cost)
                            value = valuation.former_cost * per_unit
                        else:
                            value = (line.price_unit / total_line)

                        if digits:
                            value = float_round(value, precision_digits=digits[1], rounding_method='UP')
                            fnc = min if line.price_unit > 0 else max
                            value = fnc(value, line.price_unit - value_split)
                            value_split += value

                        if valuation.id not in towrite_dict:
                            towrite_dict[valuation.id] = value
                        else:
                            towrite_dict[valuation.id] += value
        if towrite_dict:
            for key, value in towrite_dict.items():
                line_obj.write(cr, uid, key, {'additional_landed_cost': value}, context=context)
        return True

    def _track_subtype(self, cr, uid, ids, init_values, context=None):
        record = self.browse(cr, uid, ids[0], context=context)
        if 'state' in init_values and record.state == 'done':
            return 'stock_landed_costs.mt_stock_landed_cost_open'
        return super(stock_landed_cost, self)._track_subtype(cr, uid, ids, init_values, context=context)


class stock_landed_cost_lines(osv.osv):
    _name = 'stock.landed.cost.lines'
    _description = 'Stock Landed Cost Lines'

    def onchange_product_id(self, cr, uid, ids, product_id=False, context=None):
        result = {}
        if not product_id:
            return {'value': {'quantity': 0.0, 'price_unit': 0.0}}

        product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
        result['name'] = product.name
        result['split_method'] = product.split_method
        result['price_unit'] = product.standard_price
        result['account_id'] = product.property_account_expense_id and product.property_account_expense_id.id or product.categ_id.property_account_expense_categ_id.id
        return {'value': result}

    _columns = {
        'name': fields.char('Description'),
        'cost_id': fields.many2one('stock.landed.cost', 'Landed Cost', required=True, ondelete='cascade'),
        'product_id': fields.many2one('product.product', 'Product', required=True),
        'price_unit': fields.float('Cost', required=True, digits_compute=dp.get_precision('Product Price')),
        'split_method': fields.selection(product.SPLIT_METHOD, string='Split Method', required=True),
        'account_id': fields.many2one('account.account', 'Account', domain=[('internal_type', '!=', 'view'), ('internal_type', '!=', 'closed'), ('deprecated', '=', False)]),
    }

class stock_valuation_adjustment_lines(osv.osv):
    _name = 'stock.valuation.adjustment.lines'
    _description = 'Stock Valuation Adjustment Lines'

    def _amount_final(self, cr, uid, ids, name, args, context=None):
        result = {}
        for line in self.browse(cr, uid, ids, context=context):
            result[line.id] = {
                'former_cost_per_unit': 0.0,
                'final_cost': 0.0,
            }
            result[line.id]['former_cost_per_unit'] = (line.former_cost / line.quantity if line.quantity else 1.0)
            result[line.id]['final_cost'] = (line.former_cost + line.additional_landed_cost)
        return result

    def _get_name(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = line.product_id.code or line.product_id.name or ''
            if line.cost_line_id:
                res[line.id] += ' - ' + line.cost_line_id.name
        return res

    _columns = {
        'name': fields.function(_get_name, type='char', string='Description', store=True),
        'cost_id': fields.many2one('stock.landed.cost', 'Landed Cost', required=True, ondelete='cascade'),
        'cost_line_id': fields.many2one('stock.landed.cost.lines', 'Cost Line', readonly=True),
        'move_id': fields.many2one('stock.move', 'Stock Move', readonly=True),
        'product_id': fields.many2one('product.product', 'Product', required=True),
        'quantity': fields.float('Quantity', digits_compute=dp.get_precision('Product Unit of Measure'), required=True),
        'weight': fields.float('Weight', digits_compute=dp.get_precision('Product Unit of Measure')),
        'volume': fields.float('Volume', digits_compute=dp.get_precision('Product Unit of Measure')),
        'former_cost': fields.float('Former Cost', digits_compute=dp.get_precision('Product Price')),
        'former_cost_per_unit': fields.function(_amount_final, multi='cost', string='Former Cost(Per Unit)', type='float', store=True, digits=0),
        'additional_landed_cost': fields.float('Additional Landed Cost', digits_compute=dp.get_precision('Product Price')),
        'final_cost': fields.function(_amount_final, multi='cost', string='Final Cost', type='float', store=True, digits=0),
    }

    _defaults = {
        'quantity': 1.0,
        'weight': 1.0,
        'volume': 1.0,
    }
