from odoo import fields, models


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

    value = fields.Float(string='Value')
    company_id = fields.Many2one('res.company', string='Company')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string='Currency')
    date = fields.Datetime(string='Date', default=fields.Datetime.now)

    description = fields.Char(string='Description')
