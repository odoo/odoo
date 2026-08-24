from odoo import api, fields, models


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
    product_tracking = fields.Selection(related='product_id.tracking')
    lot_id = fields.Many2one('stock.lot', string='Lot')
    move_id = fields.Many2one('stock.move', string='Move', index='btree_not_null')

    quantity = fields.Float('Quantity', digits='Product Unit')
    old_value = fields.Monetary(string='Old Value', currency_field='currency_id', default=0.0)
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

    total_value_before = fields.Monetary(string='Value Before', currency_field='currency_id', compute="_compute_details")
    total_value_after = fields.Monetary(string='Value After', currency_field='currency_id', compute="_compute_details")
    adjustment = fields.Monetary(string='Adjustment', currency_field='currency_id', compute="_compute_details")
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

    @api.depends('quantity', 'value', 'old_value')
    def _compute_details(self):
        for product_value in self:
            if product_value.move_id:
                product_value.total_value_before = product_value.old_value
                product_value.total_value_after = product_value.value
            else:
                product_value.total_value_before = product_value.old_value * product_value.quantity
                product_value.total_value_after = product_value.value * product_value.quantity
            product_value.adjustment = product_value.total_value_after - product_value.total_value_before

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

        move_ids = set()

        for pv in product_values:
            if pv.move_id:
                move_ids.add(pv.move_id.id)
            else:
                moves, _first_move_remaining_qty = pv.product_id._get_fifo_stack(pv.lot_id, pv.date)
                if moves:
                    move_ids.update(self.env['stock.move'].concat(moves).ids)

        if move_ids:
            moves = self.env['stock.move'].browse(move_ids)
            moves._set_value(recompute_date=min(moves.mapped('date')))
        return product_values

    def action_open_account_move(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Journal Entry'),
            'res_model': 'account.move',
            'res_id': self.account_move_id.id,
            'view_mode': 'form',
        }
