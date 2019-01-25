# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, fields, models, tools, _
from odoo.addons import decimal_precision as dp
from odoo.addons.stock_landed_costs.models import product
from odoo.exceptions import UserError


class StockMove(models.Model):
    _inherit = 'stock.move'

    landed_cost_value = fields.Float('Landed Cost')


class LandedCost(models.Model):
    _name = 'stock.landed.cost'
    _description = 'Stock Landed Cost'
    _inherit = 'mail.thread'

    name = fields.Char(
        'Name', default=lambda self: _('New'),
        copy=False, readonly=True, track_visibility='always')
    date = fields.Date(
        'Date', default=fields.Date.context_today,
        copy=False, required=True, states={'done': [('readonly', True)]}, track_visibility='onchange')
    picking_ids = fields.Many2many(
        'stock.picking', string='Transfers',
        copy=False, states={'done': [('readonly', True)]})
    cost_lines = fields.One2many(
        'stock.landed.cost.lines', 'cost_id', 'Cost Lines',
        copy=True, states={'done': [('readonly', True)]})
    valuation_adjustment_lines = fields.One2many(
        'stock.valuation.adjustment.lines', 'cost_id', 'Valuation Adjustments',
        states={'done': [('readonly', True)]})
    description = fields.Text(
        'Item Description', states={'done': [('readonly', True)]})
    amount_total = fields.Float(
        'Total', compute='_compute_total_amount',
        digits=0, store=True, track_visibility='always')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Posted'),
        ('cancel', 'Cancelled')], 'State', default='draft',
        copy=False, readonly=True, track_visibility='onchange')
    account_move_id = fields.Many2one(
        'account.move', 'Journal Entry',
        copy=False, readonly=True)
    account_journal_id = fields.Many2one(
        'account.journal', 'Account Journal',
        required=True, states={'done': [('readonly', True)]})
    company_id = fields.Many2one('res.company', string="Company",
        related='account_journal_id.company_id', readonly=False)

    @api.one
    @api.depends('cost_lines.price_unit')
    def _compute_total_amount(self):
        self.amount_total = sum(line.price_unit for line in self.cost_lines)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('stock.landed.cost')
        return super(LandedCost, self).create(vals)

    @api.multi
    def unlink(self):
        self.button_cancel()
        return super(LandedCost, self).unlink()

    @api.multi
    def _track_subtype(self, init_values):
        if 'state' in init_values and self.state == 'done':
            return 'stock_landed_costs.mt_stock_landed_cost_open'
        return super(LandedCost, self)._track_subtype(init_values)

    @api.multi
    def button_cancel(self):
        if any(cost.state == 'done' for cost in self):
            raise UserError(
                _('Validated landed costs cannot be cancelled, but you could create negative landed costs to reverse them'))
        return self.write({'state': 'cancel'})

    @api.multi
    def button_validate(self):
        if any(cost.state != 'draft' for cost in self):
            raise UserError(_('Only draft landed costs can be validated'))
        if any(not cost.valuation_adjustment_lines for cost in self):
            raise UserError(_('No valuation adjustments lines. You should maybe recompute the landed costs.'))
        if not self._check_sum():
            raise UserError(_('Cost and adjustments lines do not match. You should maybe recompute the landed costs.'))

        for cost in self:
            move = self.env['account.move']
            move_vals = {
                'journal_id': cost.account_journal_id.id,
                'date': cost.date,
                'ref': cost.name,
                'line_ids': [],
            }
            for line in cost.valuation_adjustment_lines.filtered(lambda line: line.move_id):
                # Prorate the value at what's still in stock
                cost_to_add = (line.move_id.remaining_qty / line.move_id.product_qty) * line.additional_landed_cost

                new_landed_cost_value = line.move_id.landed_cost_value + line.additional_landed_cost
                line.move_id.write({
                    'landed_cost_value': new_landed_cost_value,
                    'value': line.move_id.value + line.additional_landed_cost,
                    'remaining_value': line.move_id.remaining_value + cost_to_add,
                    'price_unit': (line.move_id.value + line.additional_landed_cost) / line.move_id.product_qty,
                })
                # `remaining_qty` is negative if the move is out and delivered proudcts that were not
                # in stock.
                qty_out = 0
                if line.move_id._is_in():
                    qty_out = line.move_id.product_qty - line.move_id.remaining_qty
                elif line.move_id._is_out():
                    qty_out = line.move_id.product_qty
                move_vals['line_ids'] += line._create_accounting_entries(move, qty_out)

            move = move.create(move_vals)
            cost.write({'state': 'done', 'account_move_id': move.id})
            move.post()
        return True

    def _check_sum(self):
        """ Check if each cost line its valuation lines sum to the correct amount
        and if the overall total amount is correct also """
        prec_digits = self.env.user.company_id.currency_id.decimal_places
        for landed_cost in self:
            total_amount = sum(landed_cost.valuation_adjustment_lines.mapped('additional_landed_cost'))
            if not tools.float_compare(total_amount, landed_cost.amount_total, precision_digits=prec_digits) == 0:
                return False

            val_to_cost_lines = defaultdict(lambda: 0.0)
            for val_line in landed_cost.valuation_adjustment_lines:
                val_to_cost_lines[val_line.cost_line_id] += val_line.additional_landed_cost
            if any(tools.float_compare(cost_line.price_unit, val_amount, precision_digits=prec_digits) != 0
                   for cost_line, val_amount in val_to_cost_lines.items()):
                return False
        return True

    def get_valuation_lines(self):
        lines = []

        for move in self.mapped('picking_ids').mapped('move_lines'):
            # it doesn't make sense to make a landed cost for a product that isn't set as being valuated in real time at real cost
            if move.product_id.valuation != 'real_time' or move.product_id.cost_method != 'fifo':
                continue
            vals = {
                'product_id': move.product_id.id,
                'move_id': move.id,
                'quantity': move.product_qty,
                'former_cost': move.value,
                'weight': move.product_id.weight * move.product_qty,
                'volume': move.product_id.volume * move.product_qty
            }
            lines.append(vals)

        if not lines and self.mapped('picking_ids'):
            raise UserError(_("You cannot apply landed costs on the chosen transfer(s). Landed costs can only be applied for products with automated inventory valuation and FIFO costing method."))
        return lines

    @api.multi
    def compute_landed_cost(self):
        AdjustementLines = self.env['stock.valuation.adjustment.lines']
        AdjustementLines.search([('cost_id', 'in', self.ids)]).unlink()

        digits = dp.get_precision('Product Price')(self._cr)
        towrite_dict = {}
        for cost in self.filtered(lambda cost: cost.picking_ids):
            total_qty = 0.0
            total_cost = 0.0
            total_weight = 0.0
            total_volume = 0.0
            total_line = 0.0
            all_val_line_values = cost.get_valuation_lines()
            for val_line_values in all_val_line_values:
                for cost_line in cost.cost_lines:
                    val_line_values.update({'cost_id': cost.id, 'cost_line_id': cost_line.id})
                    self.env['stock.valuation.adjustment.lines'].create(val_line_values)
                total_qty += val_line_values.get('quantity', 0.0)
                total_weight += val_line_values.get('weight', 0.0)
                total_volume += val_line_values.get('volume', 0.0)

                former_cost = val_line_values.get('former_cost', 0.0)
                # round this because former_cost on the valuation lines is also rounded
                total_cost += tools.float_round(former_cost, precision_digits=digits[1]) if digits else former_cost

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
                            value = tools.float_round(value, precision_digits=digits[1], rounding_method='UP')
                            fnc = min if line.price_unit > 0 else max
                            value = fnc(value, line.price_unit - value_split)
                            value_split += value

                        if valuation.id not in towrite_dict:
                            towrite_dict[valuation.id] = value
                        else:
                            towrite_dict[valuation.id] += value
        for key, value in towrite_dict.items():
            AdjustementLines.browse(key).write({'additional_landed_cost': value})
        return True


class LandedCostLine(models.Model):
    _name = 'stock.landed.cost.lines'
    _description = 'Stock Landed Cost Line'

    name = fields.Char('Description')
    cost_id = fields.Many2one(
        'stock.landed.cost', 'Landed Cost',
        required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', 'Product', required=True)
    price_unit = fields.Float('Cost', digits=dp.get_precision('Product Price'), required=True)
    split_method = fields.Selection(product.SPLIT_METHOD, string='Split Method', required=True)
    account_id = fields.Many2one('account.account', 'Account', domain=[('deprecated', '=', False)])

    @api.onchange('product_id')
    def onchange_product_id(self):
        if not self.product_id:
            self.quantity = 0.0
        self.name = self.product_id.name or ''
        self.split_method = self.product_id.split_method or 'equal'
        self.price_unit = self.product_id.standard_price or 0.0
        self.account_id = self.product_id.property_account_expense_id.id or self.product_id.categ_id.property_account_expense_categ_id.id


class AdjustmentLines(models.Model):
    _name = 'stock.valuation.adjustment.lines'
    _description = 'Valuation Adjustment Lines'

    name = fields.Char(
        'Description', compute='_compute_name', store=True)
    cost_id = fields.Many2one(
        'stock.landed.cost', 'Landed Cost',
        ondelete='cascade', required=True)
    cost_line_id = fields.Many2one(
        'stock.landed.cost.lines', 'Cost Line', readonly=True)
    move_id = fields.Many2one('stock.move', 'Stock Move', readonly=True)
    product_id = fields.Many2one('product.product', 'Product', required=True)
    quantity = fields.Float(
        'Quantity', default=1.0,
        digits=0, required=True)
    weight = fields.Float(
        'Weight', default=1.0,
        digits=dp.get_precision('Stock Weight'))
    volume = fields.Float(
        'Volume', default=1.0)
    former_cost = fields.Float(
        'Former Cost', digits=dp.get_precision('Product Price'))
    former_cost_per_unit = fields.Float(
        'Former Cost(Per Unit)', compute='_compute_former_cost_per_unit',
        digits=0, store=True)
    additional_landed_cost = fields.Float(
        'Additional Landed Cost',
        digits=dp.get_precision('Product Price'))
    final_cost = fields.Float(
        'Final Cost', compute='_compute_final_cost',
        digits=0, store=True)

    @api.one
    @api.depends('cost_line_id.name', 'product_id.code', 'product_id.name')
    def _compute_name(self):
        name = '%s - ' % (self.cost_line_id.name if self.cost_line_id else '')
        self.name = name + (self.product_id.code or self.product_id.name or '')

    @api.one
    @api.depends('former_cost', 'quantity')
    def _compute_former_cost_per_unit(self):
        self.former_cost_per_unit = self.former_cost / (self.quantity or 1.0)

    @api.one
    @api.depends('former_cost', 'additional_landed_cost')
    def _compute_final_cost(self):
        self.final_cost = self.former_cost + self.additional_landed_cost

    def _create_accounting_entries(self, move, qty_out):
        # TDE CLEANME: product chosen for computation ?
        cost_product = self.cost_line_id.product_id
        if not cost_product:
            return False
        accounts = self.product_id.product_tmpl_id.get_product_accounts()
        debit_account_id = accounts.get('stock_valuation') and accounts['stock_valuation'].id or False
        # If the stock move is dropshipped move we need to get the cost account instead the stock valuation account
        if self.move_id._is_dropshipped():
            debit_account_id = accounts.get('expense') and accounts['expense'].id or False
        already_out_account_id = accounts['stock_output'].id
        credit_account_id = self.cost_line_id.account_id.id or cost_product.property_account_expense_id.id or cost_product.categ_id.property_account_expense_categ_id.id

        if not credit_account_id:
            raise UserError(_('Please configure Stock Expense Account for product: %s.') % (cost_product.name))

        return self._create_account_move_line(move, credit_account_id, debit_account_id, qty_out, already_out_account_id)

    def _create_account_move_line(self, move, credit_account_id, debit_account_id, qty_out, already_out_account_id):
        """
        Generate the account.move.line values to track the landed cost.
        Afterwards, for the goods that are already out of stock, we should create the out moves
        """
        AccountMoveLine = []

        base_line = {
            'name': self.name,
            'product_id': self.product_id.id,
            'quantity': 0,
        }
        debit_line = dict(base_line, account_id=debit_account_id)
        credit_line = dict(base_line, account_id=credit_account_id)
        diff = self.additional_landed_cost
        if diff > 0:
            debit_line['debit'] = diff
            credit_line['credit'] = diff
        else:
            # negative cost, reverse the entry
            debit_line['credit'] = -diff
            credit_line['debit'] = -diff
        AccountMoveLine.append([0, 0, debit_line])
        AccountMoveLine.append([0, 0, credit_line])

        # Create account move lines for quants already out of stock
        if qty_out > 0:
            debit_line = dict(base_line,
                              name=(self.name + ": " + str(qty_out) + _(' already out')),
                              quantity=0,
                              account_id=already_out_account_id)
            credit_line = dict(base_line,
                               name=(self.name + ": " + str(qty_out) + _(' already out')),
                               quantity=0,
                               account_id=debit_account_id)
            diff = diff * qty_out / self.quantity
            if diff > 0:
                debit_line['debit'] = diff
                credit_line['credit'] = diff
            else:
                # negative cost, reverse the entry
                debit_line['credit'] = -diff
                credit_line['debit'] = -diff
            AccountMoveLine.append([0, 0, debit_line])
            AccountMoveLine.append([0, 0, credit_line])

            # TDE FIXME: oh dear
            if self.env.user.company_id.anglo_saxon_accounting:
                debit_line = dict(base_line,
                                  name=(self.name + ": " + str(qty_out) + _(' already out')),
                                  quantity=0,
                                  account_id=credit_account_id)
                credit_line = dict(base_line,
                                   name=(self.name + ": " + str(qty_out) + _(' already out')),
                                   quantity=0,
                                   account_id=already_out_account_id)

                if diff > 0:
                    debit_line['debit'] = diff
                    credit_line['credit'] = diff
                else:
                    # negative cost, reverse the entry
                    debit_line['credit'] = -diff
                    credit_line['debit'] = -diff
                AccountMoveLine.append([0, 0, debit_line])
                AccountMoveLine.append([0, 0, credit_line])

        return AccountMoveLine
