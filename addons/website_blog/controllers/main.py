# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013-Today OpenERP SA (<http://www.openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website.models import website
from openerp.tools.translate import _
from openerp.tools.safe_eval import safe_eval

import simplejson
import werkzeug


class WebsiteBlog(http.Controller):
    _category_post_per_page = 6
    _post_comment_per_page = 6

    @website.route([
        '/blog/',
        '/blog/page/<int:page>/',
        '/blog/<model("blog.post"):blog_post>/',
        '/blog/<model("blog.post"):blog_post>/page/<int:page>/',
        '/blog/cat/<model("blog.category"):category>/',
        '/blog/cat/<model("blog.category"):category>/page/<int:page>/',
        '/blog/tag/<model("blog.tag"):tag>/',
        '/blog/tag/<model("blog.tag"):tag>/page/<int:page>/',
    ], type='http', auth="public", multilang=True)
    def blog(self, category=None, blog_post=None, tag=None, page=1, enable_editor=None):
        """ Prepare all values to display the blog.

        :param category: category currently browsed.
        :param tag: tag that is currently used to filter blog posts
        :param blog_post: blog post currently browsed. If not set, the user is
                          browsing the category and a post pager is calculated.
                          If set the user is reading the blog post and a
                          comments pager is calculated.
        :param integer page: current page of the pager. Can be the category or
                            post pager.
        :param dict post: kwargs, may contain

         - 'enable_editor': editor control

        :return dict values: values for the templates, containing

         - 'blog_post': browse of the current post, if blog_post_id
         - 'blog_posts': list of browse records that are the posts to display
                         in a given category, if not blog_post_id
         - 'category': browse of the current category, if category_id
         - 'categories': list of browse records of categories
         - 'pager': the pager to display, posts pager in a category or comments
                    pager in a blog post
         - 'tag': current tag, if tag_id
         - 'nav_list': a dict [year][month] for archives navigation
        """
        cr, uid, context = request.cr, request.uid, request.context
        blog_post_obj = request.registry['blog.post']
        category_obj = request.registry['blog.category']

        blog_posts = None

        category_ids = category_obj.search(cr, uid, [], context=context)
        categories = category_obj.browse(cr, uid, category_ids, context=context)

        if blog_post:
            category = blog_post.category_id
            pager = request.website.pager(
                url="/blog/%s/" % blog_post.id,
                total=len(blog_post.website_message_ids),
                page=page,
                step=self._post_comment_per_page,
                scope=7
            )
            pager_begin = (page - 1) * self._post_comment_per_page
            pager_end = page * self._post_comment_per_page
            blog_post.website_message_ids = blog_post.website_message_ids[pager_begin:pager_end]
        else:
            if category:
                pager_url = "/blog/cat/%s/" % category.id
                blog_posts = category.blog_post_ids
            elif tag:
                pager_url = '/blog/tag/%s/' % tag.id
                blog_posts = tag.blog_post_ids
            else:
                pager_url = '/blog/'
                blog_post_ids = blog_post_obj.search(cr, uid, [], context=context)
                blog_posts = blog_post_obj.browse(cr, uid, blog_post_ids, context=context)

            pager = request.website.pager(
                url=pager_url,
                total=len(blog_posts),
                page=page,
                step=self._category_post_per_page,
                scope=7
            )
            pager_begin = (page - 1) * self._category_post_per_page
            pager_end = page * self._category_post_per_page
            blog_posts = blog_posts[pager_begin:pager_end]

        nav = {}
        for group in blog_post_obj.read_group(cr, uid, [], ['name', 'create_date'], groupby="create_date", orderby="create_date asc", context=context):
            # FIXME: vietnamese month names contain spaces. Set sail for fail.
            year = group['create_date'].split(" ")[1]
            if not year in nav:
                nav[year] = {'name': year, 'create_date_count': 0, 'months': []}
            nav[year]['create_date_count'] += group['create_date_count']
            nav[year]['months'].append(group)

        values = {
            'category': category,
            'categories': categories,
            'tag': tag,
            'blog_post': blog_post,
            'blog_posts': blog_posts,
            'pager': pager,
            'nav_list': nav,
            'enable_editor': enable_editor,
        }

        if blog_post:
            values['main_object'] = blog_post
        elif tag:
            values['main_object'] = tag
        elif category:
            values['main_object'] = category

        return request.website.render("website_blog.index", values)

    # TODO: Refactor (used in website_blog.js for archive links)
    # => the archive links should be generated server side
    @website.route(['/blog/nav'], type='http', auth="public", multilang=True)
    def nav(self, **post):
        cr, uid, context = request.cr, request.uid, request.context
        blog_post_ids = request.registry['blog.post'].search(
            cr, uid, safe_eval(post.get('domain')),
            order="create_date asc",
            limit=None,
            context=context
        )
        blog_post_data = [
            {
                'id': blog_post.id,
                'website_published': blog_post.website_published,
                'fragment': request.website.render("website_blog.blog_archive_link", {
                    'blog_post': blog_post
                }),
            }
            for blog_post in request.registry['blog.post'].browse(cr, uid, blog_post_ids, context=context)
        ]
        return simplejson.dumps(blog_post_data)

    @website.route(['/blog/<int:blog_post_id>/comment'], type='http', auth="public")
    def blog_post_comment(self, blog_post_id=None, **post):
        cr, uid, context = request.cr, request.uid, request.context
        request.registry['blog.post'].message_post(
            cr, uid, blog_post_id,
            body=post.get('comment'),
            type='comment',
            subtype='mt_comment',
            context=dict(context, mail_create_nosubcribe=True))
        return werkzeug.utils.redirect(request.httprequest.referrer + "#comments")

    @website.route(['/blog/<int:category_id>/new'], type='http', auth="public", multilang=True)
    def blog_post_create(self, category_id=None, **post):
        cr, uid, context = request.cr, request.uid, request.context
        create_context = dict(context, mail_create_nosubscribe=True)
        new_blog_post_id = request.registry['blog.post'].create(
            request.cr, request.uid, {
                'category_id': category_id,
                'name': _("Blog title"),
                'content': '',
                'website_published': False,
            }, context=create_context)
        return werkzeug.utils.redirect("/blog/%s/?enable_editor=1" % (new_blog_post_id))

    @website.route(['/blog/<int:blog_post_id>/duplicate'], type='http', auth="public")
    def blog_post_copy(self, blog_post_id=None, **post):
        cr, uid, context = request.cr, request.uid, request.context
        create_context = dict(context, mail_create_nosubscribe=True)
        new_blog_post_id = request.registry['blog.post'].copy(cr, uid, blog_post_id, {}, context=create_context)
        return werkzeug.utils.redirect("/blog/%s/?enable_editor=1" % (new_blog_post_id))
