# -*- coding: utf-8 -*-

from odoo import models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _get_product_website_url(self):
        """ Override to return the link of the booth instead of the product if the product is a booth. """
        self.ensure_one()
        if self.product_id.detailed_type == 'event_booth':
            return self.event_id.website_published and self.event_id.website_url
        return super()._get_product_website_url()
