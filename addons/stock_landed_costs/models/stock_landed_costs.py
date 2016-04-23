# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round
import odoo.addons.decimal_precision as dp
from odoo.addons.stock_landed_costs.models import product


class StockLandedCost(models.Model):
    _name = 'stock.landed.cost'
    _description = 'Stock Landed Cost'
    _inherit = 'mail.thread'

    name = fields.Char(track_visibility='always', default=lambda self: self.env['ir.sequence'].next_by_code('stock.landed.cost'), readonly=True, copy=False)
    date = fields.Date(required=True, states={'done': [('readonly', True)]}, default=fields.Date.context_today, track_visibility='onchange', copy=False)
    picking_ids = fields.Many2many('stock.picking', string='Pickings', states={'done': [('readonly', True)]}, copy=False)
    cost_lines = fields.One2many('stock.landed.cost.lines', 'cost_id', string='Cost Lines', states={'done': [('readonly', True)]})
    valuation_adjustment_lines = fields.One2many('stock.valuation.adjustment.lines', 'cost_id', string='Valuation Adjustments', states={'done': [('readonly', True)]})
    description = fields.Text(string='Item Description', states={'done': [('readonly', True)]})
    amount_total = fields.Float(compute='_compute_amount_total', string='Total', digits=dp.get_precision('Account'), store=True, track_visibility='always')
    state = fields.Selection([('draft', 'Draft'), ('done', 'Posted'), ('cancel', 'Cancelled')], default='draft', readonly=True, track_visibility='onchange', copy=False)
    account_move_id = fields.Many2one('account.move', string='Journal Entry', readonly=True, copy=False)
    account_journal_id = fields.Many2one('account.journal', string='Account Journal', required=True)

    @api.depends('cost_lines', 'cost_lines.price_unit', 'cost_lines.cost_id')
    def _compute_amount_total(self):
        for cost in self:
            cost.amount_total = sum(cost.cost_lines.mapped('price_unit'))

    def get_valuation_lines(self, picking_ids=None):
        lines = []
        if not picking_ids:
            return lines

        for picking in picking_ids:
            for move in picking.move_lines.filtered(lambda move: move.product_id.valuation == 'real_time' or move.product_id.cost_method == 'real'):
                #it doesn't make sense to make a landed cost for a product that isn't set as being valuated in real time at real cost
                weight = move.product_id.weight * move.product_qty
                volume = move.product_id.volume * move.product_qty
                total_cost = sum([quant.cost * quant.qty for quant in move.quant_ids])
                vals = dict(product_id=move.product_id.id, move_id=move.id, quantity=move.product_qty, former_cost=total_cost, weight=weight, volume=volume)
                lines.append(vals)
        if not lines:
            raise UserError(_('The selected picking does not contain any move that would be impacted by landed costs. Landed costs are only possible for products configured in real time valuation with real price costing method. Please make sure it is the case, or you selected the correct picking'))
        return lines

    def _create_accounting_entries(self, line, move, qty_out):
        cost_product = line.cost_line_id.product_id
        if not cost_product:
            return False
        accounts = line.product_id.product_tmpl_id.get_product_accounts()
        debit_account_id = accounts.get('stock_valuation', False) and accounts['stock_valuation'].id
        already_out_account_id = accounts.get('stock_output', False) and accounts['stock_output'].id
        credit_account_id = line.cost_line_id.account_id.id or cost_product.property_account_expense_id.id or cost_product.categ_id.property_account_expense_categ_id.id

        if not credit_account_id:
            raise UserError(_('Please configure Stock Expense Account for product: %s.') % (cost_product.name))
        return self._create_account_move_line(line, move, credit_account_id, debit_account_id, qty_out, already_out_account_id)

    def _create_account_move_line(self, line, move, credit_account_id, debit_account_id, qty_out, already_out_account_id):
        """
        Generate the account.move.line values to track the landed cost.
        Afterwards, for the goods that are already out of stock, we should create the out moves
        """
        AccountMoveLine = self.env['account.move.line'].with_context(check_move_validity=False)
        base_line = {
            'name': line.name,
            'move_id': move.id,
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
        AccountMoveLine.create(debit_line)
        AccountMoveLine.create(credit_line)
        
        #Create account move lines for quants already out of stock
        if qty_out > 0:
            debit_line = dict(base_line,
                              name=(line.name + ": " + str(qty_out) + _(' already out')),
                              quantity=qty_out,
                              account_id=already_out_account_id)
            credit_line = dict(base_line,
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
            AccountMoveLine.create(debit_line)
            AccountMoveLine.create(credit_line)
            if self.env.user.company_id.anglo_saxon_accounting:
                debit_line = dict(base_line,
                                  name=(line.name + ": " + str(qty_out) + _(' already out')),
                                  quantity=qty_out,
                                  account_id=credit_account_id)
                credit_line = dict(base_line,
                                  name=(line.name + ": " + str(qty_out) + _(' already out')),
                                  quantity=qty_out,
                                  account_id=already_out_account_id)

                if diff > 0:
                    debit_line['debit'] = diff
                    credit_line['credit'] = diff
                else:
                    # negative cost, reverse the entry
                    debit_line['credit'] = -diff
                    credit_line['debit'] = -diff
                AccountMoveLine.create(debit_line)
                AccountMoveLine.create(credit_line)
        move.assert_balanced()
        return True

    def _create_account_move(self):
        self.ensure_one()
        return self.env['account.move'].create({
            'journal_id': self.account_journal_id.id,
            'date': self.date,
            'ref': self.name
        })

    def _check_sum(self):
        """
        Will check if each cost line its valuation lines sum to the correct amount
        and if the overall total amount is correct also
        """
        self.ensure_one()
        correctcost = {}
        total = 0
        for valuation_line in self.valuation_adjustment_lines:
            if correctcost.get(valuation_line.cost_line_id):
                correctcost[valuation_line.cost_line_id] += valuation_line.additional_landed_cost
            else:
                correctcost[valuation_line.cost_line_id] = valuation_line.additional_landed_cost
            total += valuation_line.additional_landed_cost

        prec = self.env['decimal.precision'].precision_get('Account')
        # float_compare returns 0 for equal amounts
        res = not bool(float_compare(total, self.amount_total, precision_digits=prec))
        for costl in correctcost.keys():
            if float_compare(correctcost[costl], costl.price_unit, precision_digits=prec):
                res = False
        return res

    @api.multi
    def button_validate(self):
        for cost in self:
            if cost.state != 'draft':
                raise UserError(_('Only draft landed costs can be validated'))
            if not cost.valuation_adjustment_lines or not cost._check_sum():
                raise UserError(_('You cannot validate a landed cost which has no valid valuation adjustments lines. Did you click on Compute?'))
            move = cost._create_account_move()

            for line in cost.valuation_adjustment_lines.filtered(lambda line: line.move_id):
                qty_out = 0
                per_unit = line.final_cost / line.quantity
                diff = per_unit - line.former_cost_per_unit
                for quant in line.move_id.quant_ids:
                    quant.cost += diff
                qty_out = sum([quant.qty for quant in line.move_id.quant_ids if quant.location_id.usage != 'internal'])
                cost._create_accounting_entries(line, move, qty_out)
            cost.write({'state': 'done', 'account_move_id': move.id})
            cost.account_move_id.post()
        return True

    @api.multi
    def button_cancel(self):
        for cost in self:
            if cost.state == 'done':
                raise UserError(_('Validated landed costs cannot be cancelled, '
                                'but you could create negative landed costs to reverse them'))
            cost.write({'state': 'cancel'})
        return True

    @api.multi
    def unlink(self):
        # cancel or raise first
        self.button_cancel()
        return super(StockLandedCost, self).unlink()

    @api.multi
    def compute_landed_cost(self):
        self.ensure_one()
        StockValuationLine = self.env['stock.valuation.adjustment.lines']
        total_qty = total_cost = total_weight = total_volume = total_line = 0.0
        digits = dp.get_precision('Product Price')(self.env.cr)
        self.valuation_adjustment_lines.unlink()
        for cost in self.filtered(lambda cost: cost.picking_ids):
            for v in cost.get_valuation_lines(picking_ids=cost.picking_ids):
                for line in cost.cost_lines:
                    v.update({'cost_id': cost.id, 'cost_line_id': line.id})
                    StockValuationLine.create(v)
                total_qty += v.get('quantity', 0.0)
                total_cost += v.get('former_cost', 0.0)
                total_weight += v.get('weight', 0.0)
                total_volume += v.get('volume', 0.0)
                total_line += 1
            for line in cost.cost_lines:
                value_split = 0.0
                for valuation in cost.valuation_adjustment_lines.filtered(lambda l: l.cost_line_id.id == line.id):
                    value = 0.0
                    if line.split_method == 'by_quantity' and total_qty:
                        value = valuation.quantity * (line.price_unit / total_qty)
                    elif line.split_method == 'by_weight' and total_weight:
                        value = valuation.weight * (line.price_unit / total_weight)
                    elif line.split_method == 'by_volume' and total_volume:
                        value = valuation.volume * (line.price_unit / total_volume)
                    elif line.split_method == 'by_current_cost_price' and total_cost:
                        value = valuation.former_cost * (line.price_unit / total_cost)
                    else:
                        value = (line.price_unit / total_line)

                    if digits:
                        value = float_round(value, precision_digits=digits[1], rounding_method='UP')
                        fnc = min if line.price_unit > 0 else max
                        value = fnc(value, line.price_unit - value_split)
                        value_split += value

                    valuation.additional_landed_cost += value
        return True

    @api.multi
    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'state' in init_values and self.state == 'done':
            return 'stock_landed_costs.mt_stock_landed_cost_open'
        return super(StockLandedCost, self)._track_subtype(init_values)


class StockLandedCostLines(models.Model):
    _name = 'stock.landed.cost.lines'
    _description = 'Stock Landed Cost Lines'

    name = fields.Char(string='Description')
    cost_id = fields.Many2one('stock.landed.cost', string='Landed Cost', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    price_unit = fields.Float(string='Cost', required=True, digits=dp.get_precision('Product Price'))
    split_method = fields.Selection(product.SPLIT_METHOD, string='Split Method', required=True)
    account_id = fields.Many2one('account.account', string='Account', domain=[('internal_type', '!=', 'view'), ('internal_type', '!=', 'closed'), ('deprecated', '=', False)])

    @api.onchange('product_id')
    def onchange_product_id(self):
        if not self.product_id:
            self.quantity = 0.0
            self.price_unit = 0.0
        self.name = self.product_id.name
        self.split_method = self.product_id.split_method
        self.price_unit = self.product_id.standard_price
        self.account_id = self.product_id.property_account_expense_id or self.product_id.categ_id.property_account_expense_categ_id


class StockValuationAdjustmentLines(models.Model):
    _name = 'stock.valuation.adjustment.lines'
    _description = 'Stock Valuation Adjustment Lines'

    name = fields.Char(compute='_compute_name', string='Description', store=True)
    cost_id = fields.Many2one('stock.landed.cost', string='Landed Cost', required=True, ondelete='cascade')
    cost_line_id = fields.Many2one('stock.landed.cost.lines', string='Cost Line', readonly=True)
    move_id = fields.Many2one('stock.move', string='Stock Move', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    quantity = fields.Float(digits=dp.get_precision('Product Unit of Measure'), default=1.0, required=True)
    weight = fields.Float(digits=dp.get_precision('Product Unit of Measure'), default=1.0)
    volume = fields.Float(digits=dp.get_precision('Product Unit of Measure'), default=1.0)
    former_cost = fields.Float(digits=dp.get_precision('Product Price'))
    former_cost_per_unit = fields.Float(compute='_compute_final_cost', string='Former Cost(Per Unit)', digits=dp.get_precision('Account'), store=True)
    additional_landed_cost = fields.Float(digits=dp.get_precision('Product Price'))
    final_cost = fields.Float(compute='_compute_final_cost', digits=dp.get_precision('Account'), store=True)

    @api.depends('former_cost', 'quantity', 'additional_landed_cost')
    def _compute_final_cost(self):
        for line in self:
            line.former_cost_per_unit = (line.former_cost / line.quantity if line.quantity else 1.0)
            line.final_cost = (line.former_cost + line.additional_landed_cost)

    @api.depends('product_id', 'cost_line_id')
    def _compute_name(self):
        for line in self:
            line_name = line.product_id.code or line.product_id.name or ''
            if line.cost_line_id:
                line_name += ' - ' + line.cost_line_id.name
            line.name = line_name
