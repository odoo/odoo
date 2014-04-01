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

import datetime
import werkzeug

from openerp import tools
from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website.models.website import slug
from openerp.osv.orm import browse_record
from openerp.tools.translate import _
from openerp import SUPERUSER_ID


class QueryURL(object):
    def __init__(self, path='', path_args=None, **args):
        self.path = path
        self.args = args
        self.path_args = set(path_args or [])

    def __call__(self, path=None, path_args=None, **kw):
        if not path:
            path = self.path
        for k, v in self.args.items():
            kw.setdefault(k, v)
        path_args = set(path_args or []).union(self.path_args)
        paths, fragments = [], []
        for key, value in kw.items():
            if value and key in path_args:
                if isinstance(value, browse_record):
                    paths.append((key, slug(value)))
                else:
                    paths.append((key, value))
            elif value:
                if isinstance(value, list) or isinstance(value, set):
                    fragments.append(werkzeug.url_encode([(key, item) for item in value]))
                else:
                    fragments.append(werkzeug.url_encode([(key, value)]))
        if paths:
            for key, value in paths:
                path += '/' + key + '/%s' % value
        if fragments:
            path += '?' + '&'.join(fragments)
        return path


class WebsiteBlog(http.Controller):
    _blog_post_per_page = 6
    _post_comment_per_page = 6

    def nav_list(self):
        blog_post_obj = request.registry['blog.post']
        groups = blog_post_obj.read_group(request.cr, request.uid, [], ['name', 'create_date'],
            groupby="create_date", orderby="create_date asc", context=request.context)
        for group in groups:
            begin_date = datetime.datetime.strptime(group['__domain'][0][2], tools.DEFAULT_SERVER_DATETIME_FORMAT).date()
            end_date = datetime.datetime.strptime(group['__domain'][1][2], tools.DEFAULT_SERVER_DATETIME_FORMAT).date()
            group['date_begin'] = '%s' % datetime.date.strftime(begin_date, tools.DEFAULT_SERVER_DATE_FORMAT)
            group['date_end'] = '%s' % datetime.date.strftime(end_date, tools.DEFAULT_SERVER_DATE_FORMAT)
        return groups

    @http.route([
        '/blog',
        '/blog/page/<int:page>',
    ], type='http', auth="public", website=True, multilang=True)
    def blogs(self, page=1, **post):
        cr, uid, context = request.cr, request.uid, request.context
        blog_obj = request.registry['blog.post']
        total = blog_obj.search(cr, uid, [], count=True, context=context)
        pager = request.website.pager(
            url='/blog',
            total=total,
            page=page,
            step=self._blog_post_per_page,
        )
        post_ids = blog_obj.search(cr, uid, [], offset=(page-1)*self._blog_post_per_page, limit=self._blog_post_per_page, context=context)
        posts = blog_obj.browse(cr, uid, post_ids, context=context)
        current_url = QueryURL('', ['blog', 'tag'])
        return request.website.render("website_blog.latest_blogs", {
            'posts': posts,
            'pager': pager,
            'current_url': current_url,
        })

    @http.route([
        '/blog/<model("blog.blog"):blog>',
        '/blog/<model("blog.blog"):blog>/page/<int:page>',
        '/blog/<model("blog.blog"):blog>/tag/<model("blog.tag"):tag>',
        '/blog/<model("blog.blog"):blog>/tag/<model("blog.tag"):tag>/page/<int:page>',
    ], type='http', auth="public", website=True, multilang=True)
    def blog(self, blog=None, tag=None, page=1, **opt):
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
        date_begin, date_end = opt.get('date_begin'), opt.get('date_end')

        cr, uid, context = request.cr, request.uid, request.context
        blog_post_obj = request.registry['blog.post']

        blog_posts = None

        blog_obj = request.registry['blog.blog']
        blog_ids = blog_obj.search(cr, uid, [], order="create_date asc", context=context)
        blogs = blog_obj.browse(cr, uid, blog_ids, context=context)

        domain = []

        if blog:
            domain += [("id", "in", [post.id for post in blog.blog_post_ids])]
        if tag:
            domain += [("id", "in", [post.id for post in tag.blog_post_ids])]
        if date_begin and date_end:
            domain += [("create_date", ">=", date_begin), ("create_date", "<=", date_end)]
        current_url = QueryURL('', ['blog', 'tag'], blog=blog, tag=tag, date_begin=date_begin, date_end=date_end)

        blog_post_ids = blog_post_obj.search(cr, uid, domain, order="create_date asc", context=context)
        blog_posts = blog_post_obj.browse(cr, uid, blog_post_ids, context=context)

        pager = request.website.pager(
            url=current_url(),
            total=len(blog_posts),
            page=page,
            step=self._blog_post_per_page,
        )
        pager_begin = (page - 1) * self._blog_post_per_page
        pager_end = page * self._blog_post_per_page
        blog_posts = blog_posts[pager_begin:pager_end]

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
            'current_url': current_url,
            'date': date_begin,
        }
        return request.website.render("website_blog.blog_post_short", values)

    @http.route([
        '/blogpost/<model("blog.post"):blog_post>',
    ], type='http', auth="public", website=True, multilang=True)
    def blog_post(self, blog_post, tag_id=None, page=1, enable_editor=None, **post):
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
        """
        date_begin, date_end = post.get('date_begin'), post.get('date_end')

        pager_url = "/blogpost/%s" % blog_post.id

        pager = request.website.pager(
            url=pager_url,
            total=len(blog_post.website_message_ids),
            page=page,
            step=self._post_comment_per_page,
            scope=7
        )
        pager_begin = (page - 1) * self._post_comment_per_page
        pager_end = page * self._post_comment_per_page
        blog_post.website_message_ids = blog_post.website_message_ids[pager_begin:pager_end]

        tag = None
        if tag_id:
            tag = request.registry['blog.tag'].browse(request.cr, request.uid, tag_id, context=request.context)

        current_url = QueryURL('', ['blogpost'], blogpost=blog_post, tag_id=tag_id, date_begin=date_begin, date_end=date_end)

        cr, uid, context = request.cr, request.uid, request.context
        blog_obj = request.registry['blog.blog']
        blog_ids = blog_obj.search(cr, uid, [], context=context)
        blogs = blog_obj.browse(cr, uid, blog_ids, context=context)

        tag_obj = request.registry['blog.tag']
        tag_ids = tag_obj.search(cr, uid, [], context=context)
        tags = tag_obj.browse(cr, uid, tag_ids, context=context)

        values = {
            'blog': blog_post.blog_id,
            'blogs': blogs,
            'tags': tags,
            'tag': tag,
            'blog_post': blog_post,
            'main_object': blog_post,
            'pager': pager,
            'nav_list': self.nav_list(),
            'enable_editor': enable_editor,
            'date': date_begin,
            'current_url': current_url
        }
        return request.website.render("website_blog.blog_post_complete", values)

    @http.route(['/blogpost/comment'], type='http', auth="public", methods=['POST'], website=True)
    def blog_post_comment(self, blog_post_id=0, **post):
        cr, uid, context = request.cr, request.uid, request.context
        if post.get('comment'):
            user = request.registry['res.users'].browse(cr, SUPERUSER_ID, uid, context=context)
            group_ids = user.groups_id
            group_id = request.registry["ir.model.data"].get_object_reference(cr, uid, 'website_mail', 'group_comment')[1]
            if group_id in [group.id for group in group_ids]:
                blog_post = request.registry['blog.post']
                blog_post.check_access_rights(cr, uid, 'read')
                blog_post.message_post(
                    cr, SUPERUSER_ID, int(blog_post_id),
                    body=post.get('comment'),
                    type='comment',
                    subtype='mt_comment',
                    author_id=user.partner_id.id,
                    context=dict(context, mail_create_nosubcribe=True))
        return werkzeug.utils.redirect(request.httprequest.referrer + "#comments")

    @http.route('/blogpost/new', type='http', auth="public", website=True, multilang=True)
    def blog_post_create(self, blog_id, **post):
        cr, uid, context = request.cr, request.uid, request.context
        create_context = dict(context, mail_create_nosubscribe=True)
        new_blog_post_id = request.registry['blog.post'].create(
            request.cr, request.uid, {
                'blog_id': blog_id,
                'name': _("Blog Post Title"),
                'content': '',
                'website_published': False,
            }, context=create_context)
        return werkzeug.utils.redirect("/blogpost/%s?enable_editor=1" % new_blog_post_id)

    @http.route('/blogpost/duplicate', type='http', auth="public", website=True)
    def blog_post_copy(self, blog_post_id, **post):
        """ Duplicate a blog.

        :param blog_post_id: id of the blog post currently browsed.

        :return redirect to the new blog created
        """
        cr, uid, context = request.cr, request.uid, request.context
        create_context = dict(context, mail_create_nosubscribe=True)
        new_blog_post_id = request.registry['blog.post'].copy(cr, uid, blog_post_id, {}, context=create_context)
        return werkzeug.utils.redirect("/blogpost/%s?enable_editor=1" % new_blog_post_id)
