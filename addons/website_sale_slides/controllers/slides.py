# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_slides.controllers.main import WebsiteSlides
from odoo.http import request, route
from odoo.tools import format_amount


class WebsiteSaleSlides(WebsiteSlides):

    @route('/slides/get_course_products', type='json', auth='user')
    def get_course_products(self):
        """Return a list of the course products values with formatted price."""
        products = request.env['product.product'].search([('detailed_type', '=', 'course')])

        return [{
            'id': product.id,
            'name': f'{product.name} ({format_amount(request.env, product.list_price, product.currency_id)})',
        } for product in products]

    def _prepare_additional_channel_values(self, values, **kwargs):
        values = super(WebsiteSaleSlides, self)._prepare_additional_channel_values(values, **kwargs)
        channel = values['channel']
        if channel.enroll == 'payment' and channel.product_id:
            pricelist = request.website.get_current_pricelist()
            values['product_info'] = channel.product_id.product_tmpl_id._get_combination_info(product_id=channel.product_id.id, pricelist=pricelist)
            values['product_info']['currency_id'] = request.website.currency_id
        return values

    def _slide_channel_prepare_values(self, **kwargs):
        """Parse the values posted when we create a new course
        from website to add the selected product.
        """
        channel = super(WebsiteSaleSlides, self)._slide_channel_prepare_values(**kwargs)
        channel['enroll'] = kwargs.get('enroll')
        if channel['enroll'] == 'payment' and 'product_id' in kwargs:
            channel['product_id'] = int(kwargs['product_id'])
        return channel
