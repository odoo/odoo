# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.addons import event_booth_sale, website_sale


class ProductTemplate(event_booth_sale.ProductTemplate, website_sale.ProductTemplate):

    @api.model
    def _get_product_types_allow_zero_price(self):
        return super()._get_product_types_allow_zero_price() + ["event_booth"]
