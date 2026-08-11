from odoo import fields, models


class StockReplenishmentInfo(models.TransientModel):
    _inherit = 'stock.replenishment.info'
    _description = 'Stock delivery time information'

    sale_delay = fields.Integer(
        "Availability Time", related='product_id.sale_delay', readonly=False, related_sudo=False, required=True,
        help="Choose the maximum number of days within which the product should be available for delivery to a customer or for use in other situations."
    )
