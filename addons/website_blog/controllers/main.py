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

from openerp import SUPERUSER_ID
from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website import website
from openerp.tools.translate import _
from openerp.tools.safe_eval import safe_eval

import simplejson
import werkzeug


class website_mail(http.Controller):
    _category_post_per_page = 2
    _post_comment_per_page = 2

    @website.route([
        '/blog/',
        '/blog/<int:category_id>/',
        '/blog/<int:category_id>/<int:blog_post_id>/',
        '/blog/<int:category_id>/page/<int:page>/',
        '/blog/<int:category_id>/<int:blog_post_id>/page/<int:page>/'
    ], type='http', auth="public")
    def blog(self, category_id=None, blog_post_id=None, page=1, **post):
        cr, uid, context = request.cr, request.uid, request.context
        blog_post_obj = request.registry['blog.post']
        category_obj = request.registry['blog.category']

        values = {
            'blog_ids': None,
            'blog_id': None,
            'nav_list': dict(),
            'unable_editor': post.get('unable_editor')
        }

        # no category chosen: display categories
        categories = None
        category = None
        blog_post = None
        blog_posts = None
        pager = None
        if not category_id:
            category_ids = category_obj.search(cr, uid, [], context=context)
            categories = category_obj.browse(cr, uid, category_ids, context=context)
        # category but no post chosen: display the last ones, create pager
        elif category_id and not blog_post_id:
            pager_begin = (page - 1) * self._category_post_per_page
            pager_end = page * self._category_post_per_page
            category = category_obj.browse(cr, uid, category_id, context=context)
            blog_posts = category.blog_ids[pager_begin:pager_end]
            pager = request.website.pager(url="/blog/%s/" % category_id, total=len(category.blog_ids), page=page, step=self._category_post_per_page, scope=7)
        elif category_id and blog_post_id:
            category = category_obj.browse(cr, uid, category_id, context=context)
            blog_post = blog_post_obj.browse(cr, uid, blog_post_id, context=context)

        values.update({
            'blog_post': blog_post,
            'blog_posts': blog_posts,
            'categories': categories,
            'category': category,
            'pager': pager,
        })

        for group in blog_post_obj.read_group(cr, uid, [], ['name', 'create_date'], groupby="create_date", orderby="create_date asc", context=context):
            print 'group', group
            year = group['create_date'].split(" ")[1]
            if not values['nav_list'].get(year):
                values['nav_list'][year] = {'name': year, 'create_date_count': 0, 'months': []}
            values['nav_list'][year]['create_date_count'] += group['create_date_count']
            values['nav_list'][year]['months'].append(group)

        print values
        return request.website.render("website_blog.index", values)

    # @website.route(['/blog/nav'], type='http', auth="public")
    # def nav(self, **post):
    #     comment_ids = request.registry['mail.group'].get_public_message_ids(request.cr, request.uid, domain=safe_eval(post.get('domain')), order="create_date asc", limit=None, context=request.context)
    #     return simplejson.dumps(request.registry['mail.message'].read(request.cr, request.uid, comment_ids, ['website_published', 'subject', 'res_id'], request.context))

    @website.route(['/blog/<int:category_id>/<int:blog_post_id>/post'], type='http', auth="public")
    def blog_comment(self, category_id=None, blog_post_id=None, **post):
        cr, uid, context = request.cr, request.uid, request.context
        url = request.httprequest.host_url
        request.session.body = post.get('body')
        print category_id, blog_post_id, post
        if request.context['is_public_user']:  # purpose of this ?
            return '%s/admin#action=redirect&url=%s/blog/%s/%s/post' % (url, url, category_id, blog_post_id)

        if request.session.get('body') and blog_post_id:
            request.registry['blog.post'].message_post(
                cr, uid, blog_post_id,
                body=request.session.body,
                type='comment',
                subtype='mt_comment',
                context=dict(context, mail_create_nosubcribe=True))
            request.session.body = False

        return self.blog(category_id=category_id, blog_post_id=blog_post_id)

    @website.route(['/blog/<int:category_id>/new'], type='http', auth="public")
    def create_blog_post(self, category_id=None, **post):
        cr, uid, context = request.cr, request.uid, request.context
        create_context = dict(context, mail_create_nosubscribe=True)
        blog_id = request.registry['blog.post'].create(
            request.cr, request.uid, {
                'category_id': category_id,
                'name': _("Blog title"),
                'content': '',
                'website_published': False,
            }, context=create_context)
        return werkzeug.utils.redirect("/blog/%s/%s/?unable_editor=1" % (category_id, blog_id))

    def _find_or_create_partner(self, email, context=None):
        partner_obj = request.registry['res.partner']
        user_obj = request.registry['res.users']
        partner_ids = []
        if request.context['is_public_user'] and email:
            partner_ids = partner_obj.search(request.cr, SUPERUSER_ID, [("email", "=", email)], context=request.context)
            if not partner_ids:
                partner_ids = [partner_obj.create(request.cr, SUPERUSER_ID, {"email": email, "name": email}, request.context)]
        else:
            partner_ids = [user_obj.browse(request.cr, request.uid, request.uid, request.context).partner_id.id]
        return partner_ids

    @website.route(['/blog/<int:category_id>/subscribe'], type='http', auth="public")
    def category_subscribe(self, category_id=None, **post):
        partner_ids = self._find_or_create_partner(post.get('email'), request.context)
        category_obj = request.registry['blog.category']

        category_obj.check_access_rule(request.cr, request.uid, [category_id], 'read', request.context)
        category_obj.message_subscribe(request.cr, SUPERUSER_ID, [category_id], partner_ids, context=request.context)

        return self.blog(category_id=category_id)

    @website.route(['/blog/<int:category_id>/unsubscribe'], type='http', auth="public")
    def category_unsubscribe(self, category_id=None, **post):
        partner_ids = self._find_or_create_partner(post.get('email'), request.context)
        category_obj = request.registry['blog.category']

        category_obj.check_access_rule(request.cr, request.uid, [category_id], 'read', request.context)
        category_obj.message_unsubscribe(request.cr, SUPERUSER_ID, [category_id], partner_ids, context=request.context)

        return self.blog(category_id=category_id)

    @website.route(['/blog/<int:category_id>/<int:blog_post_id>/subscribe'], type='http', auth="public")
    def blog_post_subscribe(self, category_id=None, blog_post_id=None, **post):
        partner_ids = self._find_or_create_partner(post.get('email'), request.context)
        blog_post_obj = request.registry['blog.post']

        blog_post_obj.check_access_rule(request.cr, request.uid, [blog_post_id], 'read', request.context)
        blog_post_obj.message_subscribe(request.cr, SUPERUSER_ID, [blog_post_id], partner_ids, context=request.context)

        return self.blog(category_id=category_id, blog_post_id=blog_post_id)

    @website.route(['/blog/<int:category_id>/<int:blog_post_id>/unsubscribe'], type='http', auth="public")
    def blog_post_unsubscribe(self, category_id=None, blog_post_id=None, **post):
        partner_ids = self._find_or_create_partner(post.get('email'), request.context)
        blog_post_obj = request.registry['blog.post']

        blog_post_obj.check_access_rule(request.cr, request.uid, [blog_post_id], 'read', request.context)
        blog_post_obj.message_unsubscribe(request.cr, SUPERUSER_ID, [blog_post_id], partner_ids, context=request.context)

        return self.blog(category_id=category_id, blog_post_id=blog_post_id)
