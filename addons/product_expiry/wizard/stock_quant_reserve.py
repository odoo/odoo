from odoo import fields, models


class ReserveStockQuantLine(models.TransientModel):
    _inherit = 'stock.quant.reserve.line'

    expiration_date = fields.Datetime(related='lot_id.expiration_date')


class ReserveStockQuant(models.TransientModel):
    _inherit = 'stock.quant.reserve'

    show_expiry = fields.Boolean(related='move_id.product_id.use_expiration_date')
