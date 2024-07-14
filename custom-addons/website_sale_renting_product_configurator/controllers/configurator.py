# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from odoo.http import request, route

from odoo.addons.website_sale_product_configurator.controllers.main import WebsiteSaleProductConfiguratorController


class RentingConfiguratorController(WebsiteSaleProductConfiguratorController):

    @route()
    def show_advanced_configurator(self, *args, **kw):
        if request.env.context.get('start_date') and request.env.context.get('end_date'):
            request.update_context(
                start_date=fields.Datetime.to_datetime(request.env.context['start_date']),
                end_date=fields.Datetime.to_datetime(request.env.context['end_date']),
            )
        return super().show_advanced_configurator(*args, **kw)
