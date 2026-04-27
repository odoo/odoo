# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.http import request


class ProductPricing(models.Model):
    _inherit = 'product.pricing'

    def _get_tz(self):
        if request and request.is_frontend:
            return request.website.tz
        return super()._get_tz()
