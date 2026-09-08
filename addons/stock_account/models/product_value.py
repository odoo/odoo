from odoo import api, Command, fields, models
from odoo.exceptions import UserError


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

    product_id = fields.Many2one('product.product', string='Product', index=True)
    lot_id = fields.Many2one('stock.lot', string='Lot')
    move_id = fields.Many2one('stock.move', string='Move', index='btree_not_null')

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

    @api.model_create_multi
    def create(self, vals_list):
        now = fields.Datetime.now()
        for vals in vals_list:
            if vals.get('move_id'):
                move = self.env['stock.move'].browse(vals['move_id'])
                vals['product_id'] = move.product_id.id
                vals['quantity'] = move.quantity
                vals['old_value'] = move.value
                vals['date'] = now
                vals['description'] = self.env._('Move update from %(old_value)s to %(new_value)s for %(quantity)s by %(user)s',
                    old_value=move.value, new_value=vals['value'], quantity=move.quantity, user=self.env.user.name)

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
                debit_account_id = accounts[pv.product_id.id]['expense'].id
                credit_account_id = accounts[pv.product_id.id]['stock_valuation'].id
            else:
                debit_account_id = accounts[pv.product_id.id]['stock_valuation'].id
                credit_account_id = accounts[pv.product_id.id]['expense'].id
            name = self.env._(
                '%(user)s changed cost from %(old_value)s to %(new_value)s - %(record)s',
                user=pv.user_id.name,
                old_value=pv.old_value,
                new_value=pv.value,
                record=pv.lot_id.display_name or pv.product_id.display_name
            )
            pvs.add(pv.id)
            am_vals = {
                'journal_id': accounts[pv.product_id.id]['stock_journal'].id,
                'company_id': pv.company_id.id,
                'ref': pv.product_id.default_code,
                'move_type': 'entry',
                'line_ids': [Command.create({
                    'name': name,
                    'account_id': debit_account_id,
                    'debit': abs(pv.adjustment),
                    'credit': 0,
                    'product_id': pv.product_id.id,
                    'quantity': 0,
                    'tax_ids': [],
                }), Command.create({
                    'name': name,
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
                if pv.move_id._should_create_account_move():
                    prepare_am_vals(pv)
                move_ids.add(pv.move_id.id)
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
        move_ids = set()
        products = []
        if 'date' in vals or 'value' in vals:
            for pv in self:
                if pv.move_id:
                    move_ids.add(pv.move_id.id)
                else:
                    products.append((pv.product_id, pv.lot_id, min(pv.date, fields.Datetime.from_string(vals.get('date')) or pv.date)))
        res = super().write(vals)
        for pv in self:
            if pv.account_move_id and (pv.account_move_id.date != pv.date or pv.account_move_id.amount_total != abs(pv.adjustment)):
                pv.account_move_id.button_draft()
                pv.account_move_id.write({
                    'date': pv.date,
                    'line_ids': [Command.update(
                        line.id, {
                            'debit': abs(pv.adjustment) if line.debit != 0 else 0,
                            'credit': abs(pv.adjustment) if line.credit != 0 else 0,
                        }
                    ) for line in pv.account_move_id.line_ids],
                })
                pv.account_move_id.action_post()
        for (product_id, lot_id, date) in products:
            moves, _remaining_qty = product_id._get_fifo_stack(lot_id, date)
            move_ids.update(self.env['stock.move'].concat(moves).ids)
        if move_ids:
            moves = self.env['stock.move'].browse(move_ids)
            moves._set_value(recompute_date=min(moves.mapped('date')))
        return res

    def unlink(self):
        move_ids = set()
        for pv in self:
            if pv.move_id:
                move_ids.add(pv.move_id.id)
            else:
                moves, _remaining_qty = pv.product_id._get_fifo_stack(pv.lot_id, pv.date)
                move_ids.update(self.env['stock.move'].concat(moves).ids)
            if pv.account_move_id:
                pv.account_move_id.button_draft()
                pv.account_move_id.unlink()
        res = super().unlink()
        if move_ids:
            moves = self.env['stock.move'].browse(move_ids)
            moves._set_value(recompute_date=min(moves.mapped('date')))
        return res