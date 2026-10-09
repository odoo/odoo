from odoo import api, Command, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain


class ProductValue(models.Model):
    """ This model represents the history of manual update of a value.
    The potential update could be:
        - Modification of the product standard price
        - Modification of the lot standard price
        - Modification of the move value
    In case of modification of:
        - standard price, value contains the new standard price (by unit).
        - a move value: value contains the global value of the move.
    """
    _name = 'product.value'
    _description = 'Product Value'

    product_id = fields.Many2one('product.product', string='Product', index=True, ondelete='cascade')
    product_tracking = fields.Selection(related='product_id.tracking')
    lot_id = fields.Many2one('stock.lot', string='Lot', ondelete='cascade')
    move_id = fields.Many2one('stock.move', string='Move', index='btree_not_null', ondelete='cascade')

    quantity = fields.Float('Quantity', digits='Product Unit')
    old_cost = fields.Float('Old Unit Cost', min_display_digits='Product Price')
    new_cost = fields.Float('New Unit Cost', min_display_digits='Product Price')
    old_value = fields.Monetary(string='Old Value', currency_field='currency_id', default=0.0, compute="_compute_old_value", store=True)
    new_value = fields.Monetary(string='New Value', currency_field='currency_id', default=0.0, compute="_compute_new_value", store=True)
    adjustment = fields.Monetary(string='Adjustment', currency_field='currency_id', compute="_compute_adjustment")
    value = fields.Monetary(string='Value', currency_field='currency_id', required=True)
    company_id = fields.Many2one(
        'res.company', string='Company', compute='_compute_company_id',
        store=True, required=True, index=True, precompute=True, readonly=False)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string='Currency')
    date = fields.Datetime(string='Date', default=fields.Datetime.now, required=True)
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user, required=True)

    description = fields.Char(string='Description')

    # User Display Fields
    current_value = fields.Monetary(
        string='Current Value', currency_field='currency_id',
        related='move_id.value')
    current_value_details = fields.Char(string='Current Value Details', compute="_compute_current_value_details")
    current_value_description = fields.Text(string='Current Value Description', compute="_compute_value_description")
    computed_value_description = fields.Text(string='Computed Value Description', compute="_compute_value_description")

    account_move_id = fields.Many2one('account.move', string='Account Move', copy=False, index="btree_not_null")

    @api.depends('move_id', 'lot_id', 'product_id')
    def _compute_company_id(self):
        for product_value in self:
            if product_value.move_id:
                product_value.company_id = product_value.move_id.company_id
            elif product_value.lot_id:
                product_value.company_id = product_value.lot_id.company_id
            elif product_value.product_id:
                product_value.company_id = product_value.product_id.company_id
            else:
                product_value.company_id = self.env.company

    def _compute_current_value_details(self):
        for product_value in self:
            if not (product_value.move_id and product_value.move_id.quantity):
                product_value.current_value_details = False
                continue
            move = product_value.move_id
            quantity = move.quantity
            uom = move.uom_id.name
            price_unit = move.value / move.quantity
            product_value.current_value_details = self.env._("For %(quantity)s %(uom)s (%(price_unit)s per %(uom)s)",
                quantity=quantity, uom=uom, price_unit=price_unit)

    def _compute_value_description(self):
        for product_value in self:
            if not product_value.move_id:
                product_value.current_value_description = False
                product_value.computed_value_description = False
                continue
            product_value.current_value_description = product_value.move_id.value_justification
            product_value.computed_value_description = product_value.move_id.value_computed_justification

    @api.depends('old_cost')
    def _compute_old_value(self):
        for product_value in self:
            product_value.old_value = (product_value.old_cost or 0) * product_value.quantity

    @api.depends('new_cost')
    def _compute_new_value(self):
        for product_value in self:
            product_value.new_value = product_value.new_cost * product_value.quantity

    @api.depends('value', 'old_value', 'new_cost', 'old_cost')
    def _compute_adjustment(self):
        for product_value in self:
            if product_value.move_id:
                product_value.adjustment = product_value.new_value - product_value.old_value
            else:
                product_value.adjustment = (product_value.new_cost - product_value.old_cost) * product_value.quantity

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('move_id'):
                move = self.env['stock.move'].browse(vals['move_id'])
                vals['product_id'] = move.product_id.id
                vals['old_cost'] = move.value / (move.quantity or 1)
                vals['new_cost'] = vals['value'] / (move.quantity or 1)
                vals['quantity'] = move.remaining_qty
                vals['description'] = self.env._('%(move)s cost update from %(old_value)s to %(new_value)s for %(quantity)s by %(user)s, remaining %(remaining)s',
                    move=move.reference, old_value=move.value, new_value=vals['value'], quantity=move.quantity, user=self.env.user.name, remaining=move.remaining_qty)

        product_values = super().create(vals_list)

        accounts = {product.id: product.product_tmpl_id.get_product_accounts() for product in product_values.product_id}
        pvs = set()
        am_vals_list = []

        def prepare_am_vals(pv):
            if pv.product_id.valuation != 'real_time':
                return
            if pv.currency_id.is_zero(pv.adjustment):
                return
            if not accounts[pv.product_id.id].get('expense'):
                raise UserError(self.env._('You must set a counterpart account on your product category.'))
            if not accounts[pv.product_id.id].get('stock_valuation'):
                raise UserError(self.env._('You don\'t have any stock valuation account defined on your product category. You must define one before processing this operation.'))
            if pv.adjustment < 0:
                debit_account_id = accounts[pv.product_id.id]['stock_variation'].id
                credit_account_id = accounts[pv.product_id.id]['stock_valuation'].id
            else:
                debit_account_id = accounts[pv.product_id.id]['stock_valuation'].id
                credit_account_id = accounts[pv.product_id.id]['stock_variation'].id
            pvs.add(pv.id)
            am_vals = {
                'journal_id': accounts[pv.product_id.id]['stock_journal'].id,
                'company_id': pv.company_id.id,
                'ref': pv.product_id.default_code,
                'move_type': 'entry',
                'line_ids': [Command.create({
                    'name': pv.description,
                    'account_id': debit_account_id,
                    'debit': abs(pv.adjustment),
                    'credit': 0,
                    'product_id': pv.product_id.id,
                    'quantity': 0,
                    'tax_ids': [],
                }), Command.create({
                    'name': pv.description,
                    'account_id': credit_account_id,
                    'debit': 0,
                    'credit': abs(pv.adjustment),
                    'product_id': pv.product_id.id,
                    'quantity': 0,
                    'tax_ids': [],
                })],
            }
            am_vals_list.append(am_vals)

        move_ids = set()
        for pv in product_values:
            if pv.move_id:
                prepare_am_vals(pv)
                move_ids.add(pv.move_id.id)
                domain = Domain([
                    ('product_id', '=', pv.product_id.id),
                    ('company_id', '=', pv.company_id.id),
                    ('date', '>', min(pv.date, pv.move_id.date)),
                    ('is_out', '=', True),
                ])
                if pv.move_id.lot_ids:
                    domain &= Domain('move_line_ids.lot_id', 'in', pv.move_id.lot_ids.ids)
                out_moves = self.env['stock.move'].search(domain)
                if out_moves:
                    move_ids.update(out_moves.ids)
            else:
                moves, _first_move_remaining_qty = pv.product_id._get_fifo_stack(pv.lot_id, pv.date)
                if moves:
                    prepare_am_vals(pv)
                    move_ids.update(self.env['stock.move'].concat(moves).ids)

        if account_moves := self.env['account.move'].sudo().create(am_vals_list):
            account_moves._post()
            for pv, am in zip(self.env['product.value'].browse(pvs), account_moves):
                pv.account_move_id = am

        if move_ids:
            moves = self.env['stock.move'].browse(move_ids)
            moves._set_value(recompute_date=min(moves.mapped('date')))

        return product_values

    def write(self, vals):
        res = super().write(vals)

        if 'date' in vals or 'new_cost' in vals:
            accounts = {product.id: product.product_tmpl_id.get_product_accounts() for product in self.product_id}
            date = fields.Datetime.now()
            move_ids = set()
            for pv in self:
                if pv.move_id:
                    if 'new_cost' in vals:
                        pv.value = pv.quantity * pv.new_cost
                    move_ids.add(pv.move_id.id)
                else:
                    if 'new_cost' in vals:
                        pv.value = pv.new_cost
                    date = min(date, pv.date)
                    moves, _first_move_remaining_qty = pv.product_id._get_fifo_stack(pv.lot_id, pv.date)
                    if moves:
                        move_ids.update(self.env['stock.move'].concat(moves).ids)
                if pv.account_move_id:
                    if pv.adjustment < 0:
                        debit_account_id = accounts[pv.product_id.id]['stock_variation'].id
                        credit_account_id = accounts[pv.product_id.id]['stock_valuation'].id
                    else:
                        debit_account_id = accounts[pv.product_id.id]['stock_valuation'].id
                        credit_account_id = accounts[pv.product_id.id]['stock_variation'].id
                    pv.account_move_id.button_draft()
                    pv.account_move_id.write({
                        'date': pv.date.date(),
                        'line_ids': [Command.update(
                            line.id, {
                                'debit': abs(pv.adjustment) if line.account_id.id == debit_account_id else 0,
                                'credit': abs(pv.adjustment) if line.account_id.id == credit_account_id else 0,
                            }
                        ) for line in pv.account_move_id.line_ids],
                    })
                    pv.account_move_id.action_post()
            if move_ids:
                moves = self.env['stock.move'].browse(move_ids)
                date = min(moves.mapped('date') + [date])
                moves._set_value(recompute_date=date)

        return res

    def unlink(self):

        move_ids = set()
        for pv in self:
            if pv.move_id:
                move_ids.add(pv.move_id.id)
            else:
                moves, _first_move_remaining_qty = pv.product_id._get_fifo_stack(pv.lot_id, pv.date)
                move_ids.update(self.env['stock.move'].concat(moves).ids)
            if pv.account_move_id:
                pv.account_move_id.button_draft()
                pv.account_move_id.unlink()

        res = super().unlink()

        if move_ids:
            moves = self.env['stock.move'].browse(move_ids)
            moves._set_value(recompute_date=min(moves.mapped('date')))

        return res

    def action_open_account_move(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Journal Entry'),
            'res_model': 'account.move',
            'res_id': self.account_move_id.id,
            'view_mode': 'form',
        }
