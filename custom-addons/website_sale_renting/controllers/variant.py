# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from odoo.http import request, route

from odoo.addons.website_sale.controllers.variant import WebsiteSaleVariantController


class WebsiteSaleRentingVariantController(WebsiteSaleVariantController):

    @route()
    def get_combination_info_website(self, *args, start_date=None, end_date=None, **kwargs):
        """ Override to parse and add to context optional pickup and return dates."""
        if start_date and end_date:
            start_date = fields.Datetime.to_datetime(start_date)
            end_date = fields.Datetime.to_datetime(end_date)
            request.update_context(start_date=start_date, end_date=end_date)
        return super().get_combination_info_website(
            *args, start_date=start_date, end_date=end_date, **kwargs
        )
