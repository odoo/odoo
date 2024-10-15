# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import product


class ProductProduct(product.ProductProduct):

    image_fetch_pending = fields.Boolean(
        help="Whether an image must be fetched for this product. Handled by a cron.",
    )
