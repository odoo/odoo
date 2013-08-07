# -*- coding: utf-8 -*-

from openerp import SUPERUSER_ID
from openerp.addons.web import http
from openerp.addons.web.http import request
import werkzeug
from openerp.tools.translate import _
from openerp.tools.safe_eval import safe_eval
import simplejson

_months = {1:_("January"), 2:_("February"), 3:_("March"), 4:_("April"), 5:_("May"), 6:_("June"), 7:_("July"), 8:_("August"), 9:_("September"), 10:_("October"), 11:_("November"), 12:_("December")}


class website_mail(http.Controller):

    @http.route(['/blog', '/blog/<int:mail_group_id>/', '/blog/<int:mail_group_id>/<int:blog_id>/'], type='http', auth="public")
    def blog(self, mail_group_id=None, blog_id=None, **post):
        website = request.registry['website']
        group_obj = request.registry['mail.group']
        message_obj = request.registry['mail.message']
        user_obj = request.registry['res.users']

        values = website.get_rendering_context({
            'blog_ids': None,
            'blog_id': None,
            'nav_list': dict(),
            'prev_date': None,
            'next_date': None,
            'mail_group_id': mail_group_id,
            'subscribe': post.get('subscribe'),
            'website': website,
        })

        if request.uid != website.get_public_user().id and mail_group_id:
            message_follower_ids = group_obj.read(request.cr, request.uid, [mail_group_id], ['message_follower_ids'])[0]['message_follower_ids']
            parent_id = user_obj.browse(request.cr, SUPERUSER_ID, request.uid).partner_id.id
            values['subscribe'] = parent_id in message_follower_ids

        domain = mail_group_id and [("res_id", "=", mail_group_id)] or []

        for group in message_obj.read_group(request.cr, request.uid, domain + group_obj.get_public_blog(request.cr, request.uid), ['subject', 'date'], groupby="date", orderby="create_date asc"):
            year = group['date'].split(" ")[1]
            if not values['nav_list'].get(year):
                values['nav_list'][year] = {'name': year, 'date_count': 0, 'months': []}
            values['nav_list'][year]['date_count'] += group['date_count']
            values['nav_list'][year]['months'].append(group)

        if post.get('date'):
            ids = group_obj.get_public_message_ids(request.cr, request.uid, domain=domain + [("date", ">", post.get('date'))], order="create_date asc", limit=10)
            if ids:
                values['prev_date'] = message_obj.browse(request.cr, request.uid, ids.pop()).date
            domain += [("date", "<=", post.get('date'))]

        message_ids = group_obj.get_public_message_ids(request.cr, request.uid, domain=domain, order="create_date desc", limit=11)
        if message_ids:
            values['blog_ids'] = message_obj.browse(request.cr, request.uid, message_ids)
            if len(message_ids) > 10:
                values['next_date'] = values['blog_ids'].pop().date

        if blog_id:
            values['blog_id'] = message_obj.browse(request.cr, request.uid, blog_id)

        return website.render("website_mail.index", values)

    @http.route(['/blog/nav'], type='http', auth="public")
    def nav(self, **post):
        comment_ids = request.registry['mail.group'].get_public_message_ids(request.cr, request.uid, domain=safe_eval(post.get('domain')), order="create_date asc", limit=None)
        return simplejson.dumps(request.registry['mail.message'].read(request.cr, request.uid, comment_ids, ['website_published', 'subject', 'res_id']))

    @http.route(['/blog/publish'], type='http', auth="public")
    def publish(self, **post):
        message_id = int(post['id'])
        message_obj = request.registry['mail.message']

        blog = message_obj.browse(request.cr, request.uid, message_id)
        message_obj.write(request.cr, request.uid, [message_id], {'website_published': not blog.website_published})
        blog = message_obj.browse(request.cr, request.uid, message_id)

        return blog.website_published and "1" or "0"

    @http.route(['/blog/<int:mail_group_id>/<int:blog_id>/post'], type='http', auth="public")
    def blog_post(self, mail_group_id=None, blog_id=None, **post):
        website = request.registry['website']
        url = request.httprequest.host_url
        if post.get('body'):
            request.session.body = post.get('body')
            if request.uid == website.get_public_user().id:
                return '%s/admin#action=redirect&url=%s/blog/%s/%s/post' % (url, url, mail_group_id, blog_id)

        if 'body' in request.session and request.session.body:
            request.registry['mail.group'].message_post(request.cr, request.uid, mail_group_id,
                    body=request.session.body,
                    parent_id=blog_id,
                    website_published=blog_id and True or False,
                    type='comment',
                    subtype='mt_comment',
                    context={'mail_create_nosubsrequest.cribe': True},
                )
            request.session.body = False

        if post.get('body'):
            return '%s/blog/%s/%s/' % (url, mail_group_id, blog_id)
        else:
            return werkzeug.utils.redirect("/blog/%s/%s/" % (mail_group_id, blog_id))

    @http.route(['/blog/<int:mail_group_id>/new'], type='http', auth="public")
    def new_blog_post(self, mail_group_id=None, **post):
        blog_id = request.registry['mail.group'].message_post(request.cr, request.uid, mail_group_id,
                body=_("Blog content.<br/>Please edit this content then you can publish this blog."),
                subject=_("Blog title"),
                website_published=False,
                type='comment',
                subtype='mt_comment',
                context={'mail_create_nosubsrequest.cribe': True},
            )
        return werkzeug.utils.redirect("/blog/%s/%s/" % (mail_group_id, blog_id))

    @http.route(['/blog/<int:mail_group_id>/subscribe', '/blog/<int:mail_group_id>/<int:blog_id>/subscribe'], type='http', auth="public")
    def subscribe(self, mail_group_id=None, blog_id=None, **post):
        website = request.registry['website']
        partner_obj = request.registry['res.partner']
        group_obj = request.registry['mail.group']
        user_obj = request.registry['res.users']

        if mail_group_id and 'subscribe' in post and (post.get('email') or request.uid != website.get_public_user().id):
            if request.uid == website.get_public_user().id:
                partner_ids = partner_obj.search(request.cr, SUPERUSER_ID, [("email", "=", post.get('email'))])
                if not partner_ids:
                    partner_ids = [partner_obj.create(request.cr, SUPERUSER_ID, {"email": post.get('email'), "name": "Subscribe: %s" % post.get('email')})]
            else:
                partner_ids = [user_obj.browse(request.cr, request.uid, request.uid).partner_id.id]
            group_obj.check_access_rule(request.cr, request.uid, [mail_group_id], 'read')
            group_obj.message_subscribe(request.cr, SUPERUSER_ID, [mail_group_id], partner_ids)

        return self.blog(mail_group_id=mail_group_id, blog_id=blog_id, subscribe=post.get('email'))

    @http.route(['/blog/<int:mail_group_id>/unsubscribe', '/blog/<int:mail_group_id>/<int:blog_id>/unsubscribe'], type='http', auth="public")
    def unsubscribe(self, mail_group_id=None, blog_id=None, **post):
        website = request.registry['website']
        partner_obj = request.registry['res.partner']
        group_obj = request.registry['mail.group']
        user_obj = request.registry['res.users']

        if mail_group_id and 'unsubscribe' in post and (post.get('email') or request.uid != website.get_public_user().id):
            if request.uid == website.get_public_user().id:
                partner_ids = partner_obj.search(request.cr, SUPERUSER_ID, [("email", "=", post.get('email'))])
            else:
                partner_ids = [user_obj.browse(request.cr, request.uid, request.uid).partner_id.id]
            group_obj.check_access_rule(request.cr, request.uid, [mail_group_id], 'read')
            group_obj.message_unsubscribe(request.cr, SUPERUSER_ID, [mail_group_id], partner_ids)

        return self.blog(mail_group_id=mail_group_id, blog_id=blog_id, subscribe=None)

