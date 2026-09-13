from odoo import fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    website_id = fields.Many2one(
        comodel_name="website",
        related="sale_id.website_id",
        string="Website",
        help="Website where this order has been placed, for eCommerce orders.",
        store=True,
        readonly=True,
    )
