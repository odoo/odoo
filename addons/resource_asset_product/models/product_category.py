from odoo import fields, models


class ProductCategory(models.Model):
    _inherit = "product.category"

    log_type = fields.Selection(
        selection=[("service", "Service")],
        string="Asset Log Type",
        help="What an asset log booked on a product of this category records.",
    )
