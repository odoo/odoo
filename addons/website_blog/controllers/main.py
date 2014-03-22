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
from openerp.tools.translate import _
from openerp import SUPERUSER_ID

import werkzeug
import random
import json
from datetime import datetime
import random

from openerp.tools import html2plaintext


class WebsiteBlog(http.Controller):
    _blog_post_per_page = 20
    _post_comment_per_page = 10

    def nav_list(self):
        blog_post_obj = request.registry['blog.post']
        groups = blog_post_obj.read_group(request.cr, request.uid, [], ['name', 'create_date'],
            groupby="create_date", orderby="create_date asc", context=request.context)
        for group in groups:
            group['date'] = "%s_%s" % (group['__domain'][0][2], group['__domain'][1][2])
        return groups

    @http.route([
        '/blog',
        '/blog/page/<int:page>',
    ], type='http', auth="public", website=True, multilang=True)
    def blogs(self, page=1):
        BYPAGE = 60
        cr, uid, context = request.cr, request.uid, request.context
        blog_obj = request.registry['blog.post']
        total = blog_obj.search(cr, uid, [], count=True, context=context)
        pager = request.website.pager(
            url='/blog/',
            total=total,
            page=page,
            step=BYPAGE,
        )
        bids = blog_obj.search(cr, uid, [], offset=pager['offset'], limit=BYPAGE, context=context)
        blogs = blog_obj.browse(cr, uid, bids, context=context)
        return request.website.render("website_blog.latest_blogs", {
            'blogs': blogs,
            'pager': pager
        })

    @http.route([
        '/blog/<model("blog.blog"):blog>',
        '/blog/<model("blog.blog"):blog>/page/<int:page>',
        '/blog/<model("blog.blog"):blog>/tag/<model("blog.tag"):tag>',
        '/blog/<model("blog.blog"):blog>/tag/<model("blog.tag"):tag>/page/<int:page>',
        '/blog/<model("blog.blog"):blog>/date/<string(length=21):date>',
        '/blog/<model("blog.blog"):blog>/date/<string(length=21):date>/page/<int:page>',
        '/blog/<model("blog.blog"):blog>/tag/<model("blog.tag"):tag>/date/<string(length=21):date>',
        '/blog/<model("blog.blog"):blog>/tag/<model("blog.tag"):tag>/date/<string(length=21):date>/page/<int:page>',
    ], type='http', auth="public", website=True, multilang=True)
    def blog(self, blog=None, tag=None, date=None, page=1, **opt):
        """ Prepare all values to display the blog.

        :param blog: blog currently browsed.
        :param tag: tag that is currently used to filter blog posts
        :param integer page: current page of the pager. Can be the blog or
                            post pager.
        :param date: date currently used to filter blog posts (dateBegin_dateEnd)

        :return dict values: values for the templates, containing

         - 'blog_posts': list of browse records that are the posts to display
                         in a given blog, if not blog_post_id
         - 'blog': browse of the current blog, if blog_id
         - 'blogs': list of browse records of blogs
         - 'pager': the pager to display posts pager in a blog
         - 'tag': current tag, if tag_id
         - 'nav_list': a dict [year][month] for archives navigation
        """
        cr, uid, context = request.cr, request.uid, request.context
        blog_post_obj = request.registry['blog.post']

        blog_obj = request.registry['blog.blog']
        blog_ids = blog_obj.search(cr, uid, [], context=context)
        blogs = blog_obj.browse(cr, uid, blog_ids, context=context)

        path_filter = ""
        domain = []
        if blog:
            path_filter += "%s/" % blog.id
            domain += [("blog_id", "=", [blog.id])]
        if tag:
            path_filter += 'tag/%s/' % tag.id
            domain += [("tag_ids", "in", [tag.id])]
        if date:
            path_filter += "date/%s/" % date
            domain += [("create_date", ">=", date.split("_")[0]), ("create_date", "<=", date.split("_")[1])]

        blog_post_count = blog_post_obj.search(cr, uid, domain, count=True, context=context)
        pager = request.website.pager(
            url="/blog/%s" % path_filter,
            total=blog_post_count,
            page=page,
            step=self._blog_post_per_page,
            scope=10
        )
        blog_post_ids = blog_post_obj.search(cr, uid, domain, context=context, limit=self._blog_post_per_page, offset=pager['offset'])
        blog_posts = blog_post_obj.browse(cr, uid, blog_post_ids, context=context)

        tag_obj = request.registry['blog.tag']
        tag_ids = tag_obj.search(cr, uid, [], context=context)
        tags = tag_obj.browse(cr, uid, tag_ids, context=context)

        values = {
            'blog': blog,
            'blogs': blogs,
            'tags': tags,
            'tag': tag,
            'blog_posts': blog_posts,
            'pager': pager,
            'nav_list': self.nav_list(),
            'path_filter': path_filter,
            'date': date,
        }
        response = request.website.render("website_blog.blog_post_short", values)
        return response

    @http.route([
        '/blog/<model("blog.blog"):blog>/post/<model("blog.post"):blog_post>',
    ], type='http', auth="public", website=True, multilang=True)
    def blog_post(self, blog, blog_post, enable_editor=None, **post):
        """ Prepare all values to display the blog.

        :param blog_post: blog post currently browsed. If not set, the user is
                          browsing the blog and a post pager is calculated.
                          If set the user is reading the blog post and a
                          comments pager is calculated.
        :param blog: blog currently browsed.
        :param tag: tag that is currently used to filter blog posts
        :param integer page: current page of the pager. Can be the blog or
                            post pager.
        :param date: date currently used to filter blog posts (dateBegin_dateEnd)

         - 'enable_editor': editor control

        :return dict values: values for the templates, containing

         - 'blog_post': browse of the current post, if blog_post_id
         - 'blog': browse of the current blog, if blog_id
         - 'blogs': list of browse records of blogs
         - 'pager': the pager to display comments pager in a blog post
         - 'tag': current tag, if tag_id
         - 'nav_list': a dict [year][month] for archives navigation
         - 'next_blog': next blog post , display in footer
        """
        cr, uid, context = request.cr, request.uid, request.context
        if not blog_post.blog_id.id==blog.id:
            return request.redirect("/blog/%s/post/%s" % (blog_post.blog_id.id, blog_post.id))
        blog_post_obj = request.registry.get('blog.post')

        # Find next Post
        visited_blogs = request.httprequest.cookies.get('visited_blogs') or ''
        visited_ids = filter(None, visited_blogs.split(','))
        visited_ids = map(lambda x: int(x), visited_ids)
        if blog_post.id not in visited_ids:
            visited_ids.append(blog_post.id)
        next_post_id = blog_post_obj.search(cr, uid, [
            ('id', 'not in', visited_ids),
            ], order='ranking desc', limit=1, context=context)
        next_post = next_post_id and blog_post_obj.browse(cr, uid, next_post_id[0], context=context) or False

        values = {
            'blog': blog,
            'blog_post': blog_post,
            'main_object': blog_post,
            'enable_editor': enable_editor,
            'next_post' : next_post,
        }
        response = request.website.render("website_blog.blog_post_complete", values)
        response.set_cookie('visited_blogs', ','.join(map(str, visited_ids)))

        # Increase counter and ranking ratio for order
        d = datetime.now() - datetime.strptime(blog_post.create_date, "%Y-%m-%d %H:%M:%S")
        blog_post_obj.write(cr, SUPERUSER_ID, [blog_post.id], {
            'visits': blog_post.visits+1,
            'ranking': blog_post.visits * (0.5+random.random()) / max(3, d.days)
        },context=context)
        return response

    def _blog_post_message(self, user, blog_post_id=0, **post):
        cr, uid, context = request.cr, request.uid, request.context
        blog_post = request.registry['blog.post']
        message_id = blog_post.message_post(
            cr, uid, int(blog_post_id),
            body=post.get('comment'),
            type='comment',
            subtype='mt_comment',
            author_id= user.partner_id.id,
            discussion=post.get('discussion'),
            context=dict(context, mail_create_nosubcribe=True))
        return message_id

    @http.route(['/blogpost/comment'], type='http', auth="public", methods=['POST'], website=True)
    def blog_post_comment(self, blog_post_id=0, **post):
        cr, uid, context = request.cr, request.uid, request.context
        if post.get('comment'):
            user = request.registry['res.users'].browse(cr, uid, uid, context=context)
            blog_post = request.registry['blog.post']
            blog_post.check_access_rights(cr, uid, 'read')
            self._blog_post_message(user, blog_post_id, **post)
        return werkzeug.utils.redirect(request.httprequest.referrer + "#comments")

    @http.route(['/blogpost/post_discussion'], type='json', auth="public", website=True)
    def post_discussion(self, blog_post_id=0, **post):
        cr, uid, context = request.cr, request.uid, request.context
        values = []
        if post.get('comment'):
            user = request.registry['res.users'].browse(cr, uid, uid, context=context)
            id = self._blog_post_message(user, blog_post_id, **post)
            mail_obj = request.registry.get('mail.message')
            post = mail_obj.browse(cr, uid, id)
            values = {
                "author_name": post.author_id.name,
                "date": post.date,
                "body": html2plaintext(post.body),
                "author_image": "data:image/png;base64,%s" % post.author_id.image,
                }
        return values
    
    @http.route('/blogpost/new', type='http', auth="public", website=True, multilang=True)
    def blog_post_create(self, blog_id, **post):
        cr, uid, context = request.cr, request.uid, request.context
        create_context = dict(context, mail_create_nosubscribe=True)
        new_blog_post_id = request.registry['blog.post'].create(cr, uid, {
                'blog_id': blog_id,
                'name': _("Blog Post Title"),
                'sub_title': _("Subtitle"),
                'content': '',
                'website_published': False,
            }, context=create_context)
        return werkzeug.utils.redirect("/blog/%s/post/%s/?enable_editor=1" % (blog_id, new_blog_post_id))

    @http.route('/blogpost/duplicate', type='http', auth="public", website=True)
    def blog_post_copy(self, blog_post_id, **post):
        """ Duplicate a blog.

        :param blog_post_id: id of the blog post currently browsed.

        :return redirect to the new blog created
        """
        cr, uid, context = request.cr, request.uid, request.context
        create_context = dict(context, mail_create_nosubscribe=True)
        nid = request.registry['blog.post'].copy(cr, uid, blog_post_id, {}, context=create_context)
        post = request.registry['blog.post'].browse(cr, uid, nid, context)
        return werkzeug.utils.redirect("/blog/%s/post/%s/?enable_editor=1" % (post.blog_id.id, nid))

    @http.route('/blogpost/get_discussion/', type='json', auth="public", website=True)
    def discussion(self, post_id=0, discussion=None, **post):
        cr, uid, context = request.cr, request.uid, request.context
        mail_obj = request.registry.get('mail.message')
        values = []
        ids = mail_obj.search(cr, uid, [('res_id', '=', int(post_id)) ,('model','=','blog.post'), ('discussion', '=', discussion)])
        if ids:
            for post in mail_obj.browse(cr, uid, ids, context=context):
                values.append({
                    "author_name": post.author_id.name,
                    "date": post.date,
                    'body': html2plaintext(post.body),
                    'author_image': "data:image/png;base64,%s" % post.author_id.image,
                })
        return values

    @http.route('/blogpsot/change_background', type='json', auth="public", website=True)
    def change_bg(self, post_id=0, image=None, **post):
        post_obj = request.registry.get('blog.post')
        values = {'content_image' : image}
        ids = post_obj.write(request.cr, request.uid, [int(post_id)], values, request.context)
        return []

