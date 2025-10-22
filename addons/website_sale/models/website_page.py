# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from odoo import api, models


class WebsitePage(models.Model):
    _inherit = 'website.page'

    @api.model
    def _allow_cache_insertion(self, layout):
        return ' data-order-id=' not in layout and super()._allow_cache_insertion(layout)

    @api.model
    def _post_process_response_from_cache(self, request, response):
        super()._post_process_response_from_cache(request, response)

        order_id = request.session.get('sale_order_id', '')
        quantity = request.session.get('website_sale_cart_quantity', 0)
        if not order_id or not quantity:
            return

        # update generated html from "webiste_sale.header_cart_link" used on all page

        my_cart_quantity_re = re.compile(r"""
            <sup\s
            class="(?P<classname>my_cart_quantity[^"]*)"
            (?P<attributes>[^>]*?)
            >
            (?P<quantity>[^<]*)
            </sup>
            """, re.VERBOSE)

        html = response.response[0]
        cache_quantity = re.search(my_cart_quantity_re, html)
        classname = cache_quantity.group('classname').replace('d-none', '') + ('' if quantity else 'd-none')
        attributes = cache_quantity.group('attributes') + (f' data-order-id="{order_id}"' if quantity else '')
        html_quantity = f'''<sup class="{classname}"{attributes}>{quantity}</sup>'''
        html = html.replace(cache_quantity.group(0), html_quantity)

        response.response = [html]
