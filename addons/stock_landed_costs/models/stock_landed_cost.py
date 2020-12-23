# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_is_zero


SPLIT_METHOD = [
    ('equal', 'Equal'),
    ('by_quantity', 'By Quantity'),
    ('by_current_cost_price', 'By Current Cost'),
    ('by_weight', 'By Weight'),
    ('by_volume', 'By Volume'),
]


class StockLandedCost(models.Model):
    _name = 'stock.landed.cost'
    _description = 'Stock Landed Cost'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def _default_account_journal_id(self):
        """Take the journal configured in the company, else fallback on the stock journal."""
        lc_journal = self.env['account.journal']
        if self.env.company.lc_journal_id:
            lc_journal = self.env.company.lc_journal_id
        else:
            lc_journal = self.env['ir.property']._get("property_stock_journal", "product.category")
        return lc_journal

    name = fields.Char(
        'Name', default=lambda self: _('New'),
        copy=False, readonly=True, tracking=True)
    date = fields.Date(
        'Date', default=fields.Date.context_today,
        copy=False, required=True, states={'done': [('readonly', True)]}, tracking=True)
    target_model = fields.Selection(
        [('picking', 'Transfers')], string="Apply On",
        required=True, default='picking',
        copy=False, states={'done': [('readonly', True)]})
    picking_ids = fields.Many2many(
        'stock.picking', string='Transfers',
        copy=False, states={'done': [('readonly', True)]})
    allowed_picking_ids = fields.Many2many('stock.picking', compute='_compute_allowed_picking_ids')
    cost_lines = fields.One2many(
        'stock.landed.cost.lines', 'cost_id', 'Cost Lines',
        copy=True, states={'done': [('readonly', True)]})
    valuation_adjustment_lines = fields.One2many(
        'stock.valuation.adjustment.lines', 'cost_id', 'Valuation Adjustments',
        states={'done': [('readonly', True)]})
    description = fields.Text(
        'Item Description', states={'done': [('readonly', True)]})
    amount_total = fields.Monetary(
        'Total', compute='_compute_total_amount',
        store=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Posted'),
        ('cancel', 'Cancelled')], 'State', default='draft',
        copy=False, readonly=True, tracking=True)
    account_move_id = fields.Many2one(
        'account.move', 'Journal Entry',
        copy=False, readonly=True)
    account_journal_id = fields.Many2one(
        'account.journal', 'Account Journal',
        required=True, states={'done': [('readonly', True)]}, default=lambda self: self._default_account_journal_id())
    company_id = fields.Many2one('res.company', string="Company",
        related='account_journal_id.company_id')
    stock_valuation_layer_ids = fields.One2many('stock.valuation.layer', 'stock_landed_cost_id')
    vendor_bill_id = fields.Many2one(
        'account.move', 'Vendor Bill', copy=False, domain=[('move_type', '=', 'in_invoice')])
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')

    @api.depends('cost_lines.price_unit')
    def _compute_total_amount(self):
        for cost in self:
            cost.amount_total = sum(line.price_unit for line in cost.cost_lines)

    @api.depends('company_id')
    def _compute_allowed_picking_ids(self):
        self.env.cr.execute("""SELECT sm.picking_id, sm.company_id
                                 FROM stock_move AS sm
                           INNER JOIN stock_valuation_layer AS svl ON svl.stock_move_id = sm.id
                                WHERE sm.picking_id IS NOT NULL""")
        valued_picking_ids_per_company = defaultdict(list)
        for res in self.env.cr.fetchall():
            valued_picking_ids_per_company[res[1]].append(res[0])
        for cost in self:
            cost.allowed_picking_ids = valued_picking_ids_per_company[cost.company_id.id]

    @api.onchange('target_model')
    def _onchange_target_model(self):
        if self.target_model != 'picking':
            self.picking_ids = False

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('stock.landed.cost')
        return super().create(vals)

    def unlink(self):
        self.button_cancel()
        return super().unlink()

    def _track_subtype(self, init_values):
        if 'state' in init_values and self.state == 'done':
            return self.env.ref('stock_landed_costs.mt_stock_landed_cost_open')
        return super()._track_subtype(init_values)

    def button_cancel(self):
        if any(cost.state == 'done' for cost in self):
            raise UserError(
                _('Validated landed costs cannot be cancelled, but you could create negative landed costs to reverse them'))
        return self.write({'state': 'cancel'})

    def button_validate(self):
        self._check_can_validate()
        cost_without_adjusment_lines = self.filtered(lambda c: not c.valuation_adjustment_lines)
        if cost_without_adjusment_lines:
            cost_without_adjusment_lines.compute_landed_cost()
        if not self._check_sum():
            raise UserError(_('Cost and adjustments lines do not match. You should maybe recompute the landed costs.'))

        for cost in self:
            cost = cost.with_company(cost.company_id)
            move = self.env['account.move']
            move_vals = {
                'journal_id': cost.account_journal_id.id,
                'date': cost.date,
                'ref': cost.name,
                'line_ids': [],
                'move_type': 'entry',
            }
            valuation_layer_ids = []
            for line in cost.valuation_adjustment_lines.filtered(lambda line: line.move_id):
                remaining_qty = sum(line.move_id.stock_valuation_layer_ids.mapped('remaining_qty'))
                linked_layer = line.move_id.stock_valuation_layer_ids[:1]

                # Prorate the value at what's still in stock
                cost_to_add = (remaining_qty / line.move_id.product_qty) * line.additional_landed_cost
                if not cost.company_id.currency_id.is_zero(cost_to_add):
                    valuation_layer = self.env['stock.valuation.layer'].create({
                        'value': cost_to_add,
                        'unit_cost': 0,
                        'quantity': 0,
                        'remaining_qty': 0,
                        'stock_valuation_layer_id': linked_layer.id,
                        'description': cost.name,
                        'stock_move_id': line.move_id.id,
                        'product_id': line.move_id.product_id.id,
                        'stock_landed_cost_id': cost.id,
                        'company_id': cost.company_id.id,
                    })
                    linked_layer.remaining_value += cost_to_add
                    valuation_layer_ids.append(valuation_layer.id)
                # Update the AVCO
                product = line.move_id.product_id
                if product.cost_method == 'average' and not float_is_zero(product.quantity_svl, precision_rounding=product.uom_id.rounding):
                    product.with_company(self.company_id).sudo().with_context(disable_auto_svl=True).standard_price += cost_to_add / product.quantity_svl
                # `remaining_qty` is negative if the move is out and delivered proudcts that were not
                # in stock.
                qty_out = 0
                if line.move_id._is_in():
                    qty_out = line.move_id.product_qty - remaining_qty
                elif line.move_id._is_out():
                    qty_out = line.move_id.product_qty
                move_vals['line_ids'] += line._create_accounting_entries(move, qty_out)

            move_vals['stock_valuation_layer_ids'] = [(6, None, valuation_layer_ids)]
            move = move.create(move_vals)
            cost.write({'state': 'done', 'account_move_id': move.id})
            move._post()

            if cost.vendor_bill_id and cost.vendor_bill_id.state == 'posted' and cost.company_id.anglo_saxon_accounting:
                all_amls = cost.vendor_bill_id.line_ids | cost.account_move_id.line_ids
                for product in cost.cost_lines.product_id:
                    accounts = product.product_tmpl_id.get_product_accounts()
                    input_account = accounts['stock_input']
                    all_amls.filtered(lambda aml: aml.account_id == input_account and not aml.full_reconcile_id).reconcile()

        return True

    def get_valuation_lines(self):
        self.ensure_one()
        lines = []

        for move in self._get_targeted_move_ids():
            # it doesn't make sense to make a landed cost for a product that isn't set as being valuated in real time at real cost
            if move.product_id.valuation != 'real_time' or move.product_id.cost_method not in ('fifo', 'average') or move.state == 'cancel':
                continue
            vals = {
                'product_id': move.product_id.id,
                'move_id': move.id,
                'quantity': move.product_qty,
                'former_cost': sum(move.stock_valuation_layer_ids.mapped('value')),
                'weight': move.product_id.weight * move.product_qty,
                'volume': move.product_id.volume * move.product_qty
            }
            lines.append(vals)

        if not lines:
            target_model_descriptions = dict(self._fields['target_model']._description_selection(self.env))
            raise UserError(_("You cannot apply landed costs on the chosen %s(s). Landed costs can only be applied for products with automated inventory valuation and FIFO or average costing method.", target_model_descriptions[self.target_model]))
        return lines

    def compute_landed_cost(self):
        AdjustementLines = self.env['stock.valuation.adjustment.lines']
        AdjustementLines.search([('cost_id', 'in', self.ids)]).unlink()

        digits = self.env['decimal.precision'].precision_get('Product Price')
        towrite_dict = {}
        for cost in self.filtered(lambda cost: cost._get_targeted_move_ids()):
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
                total_cost += tools.float_round(former_cost, precision_digits=digits) if digits else former_cost

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
                            value = tools.float_round(value, precision_digits=digits, rounding_method='UP')
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

    def action_view_stock_valuation_layers(self):
        self.ensure_one()
        domain = [('id', 'in', self.stock_valuation_layer_ids.ids)]
        action = self.env["ir.actions.actions"]._for_xml_id("stock_account.stock_valuation_layer_action")
        return dict(action, domain=domain)

    def _get_targeted_move_ids(self):
        return self.picking_ids.move_lines

    def _check_can_validate(self):
        if any(cost.state != 'draft' for cost in self):
            raise UserError(_('Only draft landed costs can be validated'))
        for cost in self:
            if not cost._get_targeted_move_ids():
                target_model_descriptions = dict(self._fields['target_model']._description_selection(self.env))
                raise UserError(_('Please define %s on which those additional costs should apply.', target_model_descriptions[cost.target_model]))

    def _check_sum(self):
        """ Check if each cost line its valuation lines sum to the correct amount
        and if the overall total amount is correct also """
        prec_digits = self.env.company.currency_id.decimal_places
        for landed_cost in self:
            total_amount = sum(landed_cost.valuation_adjustment_lines.mapped('additional_landed_cost'))
            if not tools.float_is_zero(total_amount - landed_cost.amount_total, precision_digits=prec_digits):
                return False

            val_to_cost_lines = defaultdict(lambda: 0.0)
            for val_line in landed_cost.valuation_adjustment_lines:
                val_to_cost_lines[val_line.cost_line_id] += val_line.additional_landed_cost
            if any(not tools.float_is_zero(cost_line.price_unit - val_amount, precision_digits=prec_digits)
                   for cost_line, val_amount in val_to_cost_lines.items()):
                return False
        return True


class StockLandedCostLine(models.Model):
    _name = 'stock.landed.cost.lines'
    _description = 'Stock Landed Cost Line'

    name = fields.Char('Description')
    cost_id = fields.Many2one(
        'stock.landed.cost', 'Landed Cost',
        required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', 'Product', required=True)
    price_unit = fields.Monetary('Cost', required=True)
    split_method = fields.Selection(
        SPLIT_METHOD,
        string='Split Method',
        required=True,
        help="Equal : Cost will be equally divided.\n"
             "By Quantity : Cost will be divided according to product's quantity.\n"
             "By Current cost : Cost will be divided according to product's current cost.\n"
             "By Weight : Cost will be divided depending on its weight.\n"
             "By Volume : Cost will be divided depending on its volume.")
    account_id = fields.Many2one('account.account', 'Account', domain=[('deprecated', '=', False)])
    currency_id = fields.Many2one('res.currency', related='cost_id.currency_id')

    @api.onchange('product_id')
    def onchange_product_id(self):
        self.name = self.product_id.name or ''
        self.split_method = self.product_id.product_tmpl_id.split_method_landed_cost or self.split_method or 'equal'
        self.price_unit = self.product_id.standard_price or 0.0
        accounts_data = self.product_id.product_tmpl_id.get_product_accounts()
        self.account_id = accounts_data['stock_input']


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
        digits='Stock Weight')
    volume = fields.Float(
        'Volume', default=1.0, digits='Volume')
    former_cost = fields.Monetary(
        'Original Value')
    additional_landed_cost = fields.Monetary(
        'Additional Landed Cost')
    final_cost = fields.Monetary(
        'New Value', compute='_compute_final_cost',
        store=True)
    currency_id = fields.Many2one('res.currency', related='cost_id.company_id.currency_id')

    @api.depends('cost_line_id.name', 'product_id.code', 'product_id.name')
    def _compute_name(self):
        for line in self:
            name = '%s - ' % (line.cost_line_id.name if line.cost_line_id else '')
            line.name = name + (line.product_id.code or line.product_id.name or '')

    @api.depends('former_cost', 'additional_landed_cost')
    def _compute_final_cost(self):
        for line in self:
            line.final_cost = line.former_cost + line.additional_landed_cost

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
        credit_account_id = self.cost_line_id.account_id.id or cost_product.categ_id.property_stock_account_input_categ_id.id

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

            if self.env.company.anglo_saxon_accounting:
                expense_account_id = self.product_id.product_tmpl_id.get_product_accounts()['expense'].id
                debit_line = dict(base_line,
                                  name=(self.name + ": " + str(qty_out) + _(' already out')),
                                  quantity=0,
                                  account_id=expense_account_id)
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
