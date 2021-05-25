from odoo import models, fields


class PosConfig(models.Model):
    _inherit = 'pos.config'

    iface_open_product_info = fields.Boolean(string="Open Product Info", help="Display the 'Product Info' page when a product with optional products are added in the customer cart")
