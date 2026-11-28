from odoo import models, fields


class ProductProduct(models.Model):
    _inherit = 'product.product'

    manufacturing_pid = fields.Char('Manufacturing PID', help="The manufacturer's own product reference that does not conform to an internationally recognised standard (e.g., a proprietary model code). Supplements the merchant identifier for shipping.")
