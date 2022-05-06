# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_slides.controllers.main import WebsiteSlides
from odoo.http import request


class WebsiteSaleSlides(WebsiteSlides):

    def _prepare_additional_channel_values(self, values, **kwargs):
        values = super(WebsiteSaleSlides, self)._prepare_additional_channel_values(values, **kwargs)
        channel = values['channel']
        if channel.enroll == 'payment':
            # search the product to apply ACLs, notably on published status, to avoid access errors
            product = request.env['product.product'].search([('id', '=', channel.product_id.id)]) if channel.product_id else request.env['product.product']
            if product:
                pricelist = request.website.get_current_pricelist()
                values['product_info'] = channel.product_id.product_tmpl_id._get_combination_info(product_id=channel.product_id.id, pricelist=pricelist)
                values['product_info']['currency_id'] = request.website.currency_id
            else:
                values['product_info'] = False
        return values
