# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http, _
from odoo.exceptions import AccessError, UserError
from odoo.http import request
from odoo.osv import expression

from odoo.addons.website_slides.controllers.main import WebsiteSlides


class WebsiteSaleSlides(WebsiteSlides):

    def _prepare_additional_channel_values(self, values, **kwargs):
        values = super(WebsiteSaleSlides, self)._prepare_additional_channel_values(values, **kwargs)
        channel = values['channel']
        if channel.visibility == 'payment' and channel.product_id:
            pricelist = request.website.get_current_pricelist()
            values['product_info'] = channel.product_id.product_tmpl_id._get_combination_info(product_id=channel.product_id.id, pricelist=pricelist)
            values['product_info']['currency_id'] = request.website.currency_id
        return values
