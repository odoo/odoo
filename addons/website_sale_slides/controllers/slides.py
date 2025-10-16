# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_slides.controllers.main import WebsiteSlides
from odoo.http import request, route
from odoo.tools import format_amount
from odoo.tools.json import scriptsafe as json_scriptsafe


class WebsiteSaleSlides(WebsiteSlides):

    @route('/slides/get_course_products', type='jsonrpc', auth='user')
    def get_course_products(self):
        """Return a list of the course products values with formatted price."""
        products = request.env['product.product'].search([('service_tracking', '=', 'course')])

        return [{
            'id': product.id,
            'name': f'{product.name} ({format_amount(request.env, product.list_price, product.currency_id)})',
        } for product in products]

    def _prepare_additional_channel_values(self, values, **kwargs):
        values = super(WebsiteSaleSlides, self)._prepare_additional_channel_values(values, **kwargs)
        channel = values['channel']
        payloads = list(values.get('channel_md_payloads') or [])
        if channel.enroll == 'payment':
            # search the product to apply ACLs, notably on published status, to avoid access errors
            product = request.env['product.product'].search([('id', '=', channel.product_id.id)]) if channel.product_id else request.env['product.product']
            if product:
                values['product_info'] = product._get_combination_info_variant()
                markup_data = product._to_markup_data(request.website)
                if markup_data:
                    payloads.append(markup_data)
            else:
                values['product_info'] = False
        values['channel_md_payloads'] = payloads
        values['channel_md_json'] = payloads and json_scriptsafe.dumps(payloads, indent=2)
        return values
