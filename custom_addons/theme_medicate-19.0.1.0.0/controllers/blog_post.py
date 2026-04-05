# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions (odoo@cybrosys.com)
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
from odoo import http
from odoo.http import request
from odoo.addons.website_blog.controllers.main import WebsiteBlog


class CustomBlogController(WebsiteBlog):
    @http.route([ '/blog', '/blog/page/<int:page>' ], type='http',
                auth="public", website=True)
    def blog(self, page=1, **kwargs):
        # Define domain for blog posts
        domain = [('website_published', '=', True)]

        # Get blog posts
        blog_post = request.env['blog.post']
        total_posts = blog_post.search_count(domain)

        # Pagination
        pager = request.website.pager(
            url='/blog',
            total=total_posts,
            page=page,
            step=12  # Posts per page
        )
        posts = blog_post.search(
            domain,
            limit=12,
            offset=pager['offset'],
            order='post_date desc'
        )
        # Prepare values to pass to template
        values = {
            'posts': posts,
            'pager': pager,
            'opt_blog_sidebar_show': True,  # Optional: control sidebar visibility
        }
        return request.render('website_blog.blog_post_short', values)

    @http.route(['/blog/<model("blog.post"):blog_post>'], type='http', auth="public", website=True)
    def blog_post(self, blog_post, **kwargs):
        # Values for single blog post view
        values = {
            'blog_post': blog_post,
            'opt_blog_post_sidebar': True,
        }
        return request.render('website_blog.blog_post_complete', values)


class BlogPostSearchRedirect(http.Controller):
    @http.route('/product_info', auth='public', type='json')
    def blog_post_search_match(self, query):
            post = request.env['blog.post'].sudo().search(
                [('name', 'ilike', query)],
                limit=1)
            if post:
                return {'url': post.website_url}
            return {}
