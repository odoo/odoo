# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Vishnu P(odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
import babel.dates
import itertools
import pytz
from odoo.http import request
from odoo.tools import lazy
from odoo import http, fields
from werkzeug.exceptions import NotFound
from collections import OrderedDict
from odoo.tools import sql
from odoo.tools.misc import get_lang
from odoo.addons.website.controllers.main import QueryURL
from odoo.addons.http_routing.models.ir_http import slug, unslug
from odoo.addons.website_sale.controllers.main import TableCompute, WebsiteSale


class WebsiteShop(WebsiteSale):
    """Shop Controller
        super the controller to set 3 columns of products in
        website shop instead of 4
    """
    @http.route(['/shop/config/website'], type='json', auth='user')
    def _change_website_config(self, **options):
        """
            Function for shop configuration
        """
        if not request.env.user.has_group(
                'website.group_website_restricted_editor'):
            raise NotFound()
        current_website = request.env['website'].get_current_website()
        # Restrict options we can write to.
        writable_fields = {
            'shop_ppg', 'shop_ppr', 'shop_default_sort',
            'product_page_image_layout', 'product_page_image_width',
            'product_page_grid_columns', 'product_page_image_spacing'
        }
        # Default ppg to 1.
        if 'ppg' in options and not options['ppg']:
            options['ppg'] = 1
        if 'product_page_grid_columns' in options:
            options['product_page_grid_columns'] = int(
                options['product_page_grid_columns'])
        write_vals = {k: v for k, v in options.items() if k in writable_fields}
        if write_vals:
            current_website.write(write_vals)
        current_website.select = True

    @http.route()
    def shop(self, page=0, category=None, search='', min_price=0.0,
             max_price=0.0, ppg=False, **post):
        """Function for website shop"""
        current_website = request.env['website'].get_current_website()
        if not current_website.select:
            ppg = 12
            ppr = 3
            res = super(WebsiteShop, self).shop(page=page, category=category,
                                                search=search,
                                                min_price=min_price,
                                                max_price=max_price, ppg=ppg,
                                                **post)
            products = res.qcontext['products']
            res.qcontext.update({
                'bins': lazy(
                    lambda: TableCompute().process(products, ppg, ppr)),
                'ppr': ppr,
            })
            return res
        else:
            ppg = current_website.shop_ppg
            ppr = current_website.shop_ppr
            res = super(WebsiteShop, self).shop(page=page, category=category,
                                                search=search,
                                                min_price=min_price,
                                                max_price=max_price, ppg=ppg,
                                                **post)
            products = res.qcontext['products']
            res.qcontext.update({
                'bins': lazy(
                    lambda: TableCompute().process(products, ppg, ppr)),
                'ppr': ppr,
            })
            current_website.select = True
            return res


class WebsiteBlog(http.Controller):
    """
    Class for Website blog, super the controller to get the previous blog id
    """
    def nav_list(self, blog=None):
        dom = blog and [('blog_id', '=', blog.id)] or []
        if not request.env.user.has_group('website.group_website_designer'):
            dom += [('post_date', '<=', fields.Datetime.now())]
        groups = request.env['blog.post']._read_group_raw(
            dom,
            ['name', 'post_date'],
            groupby=["post_date"], orderby="post_date desc")
        for group in groups:
            (r, label) = group['post_date']
            start, end = r.split('/')
            group['post_date'] = label
            group['date_begin'] = start
            group['date_end'] = end
            locale = get_lang(request.env).code
            start = pytz.UTC.localize(fields.Datetime.from_string(start))
            tzinfo = pytz.timezone(request.context.get('tz', 'utc') or 'utc')
            group['month'] = babel.dates.format_datetime(start, format='MMMM',
                                                         tzinfo=tzinfo,
                                                         locale=locale)
            group['year'] = babel.dates.format_datetime(start, format='yyyy',
                                                        tzinfo=tzinfo,
                                                        locale=locale)
        return OrderedDict((year, [m for m in months]) for year, months in
                           itertools.groupby(groups, lambda g: g['year']))

    @http.route([
        '''/blog/<model("blog.blog"):blog>/<model("blog.post", "[('blog_id','=',blog.id)]"):blog_post>''',
    ], type='http', auth="public", website=True, sitemap=True)
    def blog_post(self, blog, blog_post, tag_id=None, page=1,
                  enable_editor=None, **post):
        """ Prepare all values to display the blog.
        :return dict values: values for the templates, containing
         - 'blog_post': browse of the current post
         - 'blog': browse of the current blog
         - 'blogs': list of browse records of blogs
         - 'tag': current tag, if tag_id in parameters
         - 'tags': all tags, for tag-based navigation
         - 'pager': a pager on the comments
         - 'nav_list': a dict [year][month] for archives navigation
         - 'next_post': next blog post, to direct the user towards the next
                        interesting post
        """
        BlogPost = request.env['blog.post']
        date_begin, date_end = post.get('date_begin'), post.get('date_end')
        domain = request.website.website_domain()
        blogs = blog.search(domain, order="create_date, id asc")
        tag = None
        if tag_id:
            tag = request.env['blog.tag'].browse(int(tag_id))
        blog_url = QueryURL('', ['blog', 'tag'], blog=blog_post.blog_id,
                            tag=tag, date_begin=date_begin, date_end=date_end)
        if not blog_post.blog_id.id == blog.id:
            return request.redirect(
                "/blog/%s/%s" % (slug(blog_post.blog_id), slug(blog_post)),
                code=301)
        tags = request.env['blog.tag'].search([])
        # Find next Post
        blog_post_domain = [('blog_id', '=', blog.id)]
        if not request.env.user.has_group('website.group_website_designer'):
            blog_post_domain += [('post_date', '<=', fields.Datetime.now())]
        all_post = BlogPost.search(blog_post_domain)
        if blog_post not in all_post:
            return request.redirect("/blog/%s" % (slug(blog_post.blog_id)))
        # should always return at least the current post
        all_post_ids = all_post.ids
        current_blog_post_index = all_post_ids.index(blog_post.id)
        nb_posts = len(all_post_ids)
        next_post_id = all_post_ids[
            (current_blog_post_index + 1) % nb_posts] if nb_posts > 1 else None
        next_post = next_post_id and BlogPost.browse(next_post_id) or False
        prev_post_id = all_post_ids[
            (current_blog_post_index - 1) % nb_posts] if nb_posts > 1 else None
        prev_post = next_post_id and BlogPost.browse(prev_post_id) or False
        values = {
            'tags': tags,
            'tag': tag,
            'blog': blog,
            'blog_post': blog_post,
            'blogs': blogs,
            'main_object': blog_post,
            'enable_editor': enable_editor,
            'next_post': next_post,
            'date': date_begin,
            'blog_url': blog_url,
            'prev_post': prev_post,
        }
        response = request.render("website_blog.blog_post_complete", values)
        if blog_post.id not in request.session.get('posts_viewed', []):
            if sql.increment_fields_skiplock(blog_post, 'visits'):
                if not request.session.get('posts_viewed'):
                    request.session['posts_viewed'] = []
                request.session['posts_viewed'].append(blog_post.id)
                request.session.modified = True
        return response
