# -*- coding: utf-8 -*-

from odoo import http
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website_blog.controllers.main import WebsiteBlog


class WebsiteSaleBlog(WebsiteBlog):
    @http.route()
    def blog_post(self, **kw):
        response = super(WebsiteSaleBlog, self).blog_post(**kw)
        if response.status_code == 200:
            response.qcontext['pricelist'] = WebsiteSale()._get_pricelist_context()[1]
        return response
