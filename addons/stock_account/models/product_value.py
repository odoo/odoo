from odoo import _, api, fields, models


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

    product_id = fields.Many2one('product.product', string='Product')
    lot_id = fields.Many2one('stock.lot', string='Lot')
    move_id = fields.Many2one('stock.move', string='Move')

    value = fields.Monetary(string='Value', currency_field='currency_id', required=True)
    company_id = fields.Many2one('res.company', string='Company', compute='_compute_company_id', store=True, required=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string='Currency')
    date = fields.Datetime(string='Date', default=fields.Datetime.now, required=True)
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user, required=True)

    description = fields.Char(string='Description')

    # User Display Fields
    current_value = fields.Monetary(
        string='Current Value', currency_field='currency_id',
        related='move_id.value')
    current_value_details = fields.Char(string='Current Value Details', compute="_compute_current_value_details")

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
            if not product_value.move_id:
                product_value.current_value_details = False
                continue
            move = product_value.move_id
            quantity = move.quantity
            uom = move.product_uom.name
            price_unit = move.value / move.quantity
            product_value.current_value_details = _("For %(quantity)s %(uom)s (%(price_unit)s per %(uom)s)",
                quantity=quantity, uom=uom, price_unit=price_unit)

    @api.model_create_multi
    def create(self, vals_list):
        lot_ids = set()
        product_ids = set()
        move_ids = set()

        for vals in vals_list:
            if vals.get('move_id'):
                move_ids.add(vals['move_id'])
            elif vals.get('lot_id'):
                lot_ids.add(vals['lot_id'])
            else:
                product_ids.add(vals['product_id'])
        if lot_ids:
            move_ids.update(self.env['stock.move'].search([('lot_id', 'in', lot_ids)]).ids)
        products = self.env['product.product'].browse(product_ids)
        if products:
            moves_by_product = products._get_remaining_moves()
            for qty_by_move in moves_by_product.values():
                move_ids.update(self.env['stock.move'].concat(*qty_by_move.keys()).ids)

        res = super().create(vals_list)
        if move_ids:
            self.env['stock.move'].browse(move_ids)._set_value()
        return res
