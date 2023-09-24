# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo import http, fields
from odoo.http import request


class MainProduct(http.Controller):

    @http.route('/get_main_product', auth="public", type='json',
                website=True)
    def get_main_product(self):
        main_products = request.env['product.template'].sudo().search(
            [('website_published', '=', True)],
            order='create_date asc', limit=8)

        values = {
            'main_products': main_products,
        }
        response = http.Response(template='theme_fuge.product_section',
                                 qcontext=values)
        return response.render()


class WebsiteBlog(http.Controller):

    @http.route('/get_blog_post', auth="public", type='json',
                website=True)
    def get_blog_post(self):
        posts = request.env['blog.post'].sudo().search(
            [('website_published', '=', True),
             ('post_date', '<=', fields.Datetime.now())],
            order='published_date desc', limit=4)

        values = {
            'posts_recent': posts,
        }
        response = http.Response(template='theme_fuge.latest_blog',
                                 qcontext=values)
        return response.render()


class WebsiteContactUs(http.Controller):

    @http.route('/contactus-thank-you', type="http", website=True, auth='public')
    def create_contact_us(self, **kw):
        return request.render("website.contactus_thanks", {})


class WebsiteProductComparison(WebsiteSale):

    @http.route()
    def shop(self, **post):
        res = super().shop(**post)
        res_config_settings = request.env['res.config.settings'].sudo().search([], limit=1, order='id desc')
        boolean_product_comparison = res_config_settings.module_website_sale_comparison
        res.qcontext.update({'boolean_product_comparison': boolean_product_comparison})
        return res
