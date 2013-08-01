# -*- coding: utf-8 -*-

from openerp.addons.web.http import request
from openerp.addons.website import website
import werkzeug
from openerp.tools.translate import _
from openerp.tools.safe_eval import safe_eval
import simplejson

_months = {1:_("January"), 2:_("February"), 3:_("March"), 4:_("April"), 5:_("May"), 6:_("June"), 7:_("July"), 8:_("August"), 9:_("September"), 10:_("October"), 11:_("November"), 12:_("December")}


class website_mail(website):

    @website.route(['/blog', '/blog/<int:mail_group_id>', '/blog/<int:mail_group_id>/<int:blog_id>'], type='http', auth="admin")
    def blog(self, cr, uid, mail_group_id=None, blog_id=None, **post):
        group_obj = request.registry['mail.group']
        message_obj = request.registry['mail.message']

        values = {
            'res_company': request.registry['res.company'].browse(cr, uid, 1),
            'blog_ids': None,
            'blog_id': None,
            'nav_list': dict(),
            'prev_date': None,
            'next_date': None,
            'mail_group_id': mail_group_id,
        }
        domain = mail_group_id and [("res_id", "=", mail_group_id)] or []

        for group in message_obj.read_group(cr, uid, domain + group_obj.get_public_domain(cr, uid), ['subject', 'date'], groupby="date", orderby="create_date asc"):
            year = group['date'].split(" ")[1]
            if not values['nav_list'].get(year):
                values['nav_list'][year] = {'name': year, 'date_count': 0, 'months': []}
            values['nav_list'][year]['date_count'] += group['date_count']
            values['nav_list'][year]['months'].append(group)

        if post.get('date'):
            ids = group_obj.get_public_message_ids(cr, uid, domain=domain + [("date", ">", post.get('date'))], order="create_date asc", limit=10)
            if ids:
                values['prev_date'] = message_obj.browse(cr, uid, ids.pop()).date
            domain += [("date", "<=", post.get('date'))]

        message_ids = group_obj.get_public_message_ids(cr, uid, domain=domain, order="create_date desc", limit=11)
        if message_ids:
            values['blog_ids'] = message_obj.browse(cr, uid, message_ids)
            if len(message_ids) > 10:
                values['next_date'] = values['blog_ids'].pop().date

        if blog_id:
            values['blog_id'] = message_obj.browse(cr, uid, blog_id)
            comment_ids = [child_id.id for child_id in values['blog_id'].child_ids]
            values['comments'] = message_obj.read(cr, uid, comment_ids, ['website_published', 'author_id', 'date', 'body'])

        html = self.render(cr, uid, "website_mail.index", values)
        return html

    @website.route(['/blog/nav'], type='http', auth="admin")
    def nav(self, cr, uid, **post):
        comment_ids = request.registry['mail.group'].get_public_message_ids(cr, uid, domain=safe_eval(post.get('domain')), order="create_date asc", limit=None)
        return simplejson.dumps(request.registry['mail.message'].read(cr, uid, comment_ids, ['website_published', 'subject', 'res_id']))

    @website.route(['/blog/publish'], type='http', auth="admin")
    def publish(self, cr, uid, **post):
        message_id = int(post['message_id'])
        message_obj = request.registry['mail.message']

        blog = message_obj.browse(cr, uid, message_id)
        message_obj.write(cr, uid, [message_id], {'website_published': not blog.website_published})
        blog = message_obj.browse(cr, uid, message_id)

        return blog.website_published and "1" or "0"

    @website.route(['/blog/<int:mail_group_id>/<int:blog_id>/post'], type='http', auth="admin")
    def blog_post(self, cr, uid, mail_group_id=None, blog_id=None, **post):
        url = request.httprequest.host_url
        if post.get('body'):
            request.session.body = post.get('body')
            if not self.isloggued():
                return '%s/admin#action=redirect&url=%s/blog/%s/%s/post' % (url, url, mail_group_id, blog_id)

        if 'body' in request.session and request.session.body:
            request.registry['mail.group'].message_post(cr, uid, mail_group_id,
                    body=request.session.body,
                    parent_id=blog_id,
                    website_published=blog_id and True or False,
                    type='comment',
                    subtype='mt_comment',
                    context={'mail_create_nosubscribe': True},
                )
            request.session.body = False

        if post.get('body'):
            return '%s/blog/%s/%s' % (url, mail_group_id, blog_id)
        else:
            return werkzeug.utils.redirect("/blog/%s/%s" % (mail_group_id, blog_id))

    @website.route(['/blog/<int:mail_group_id>/new'], type='http', auth="admin")
    def new_blog_post(self, cr, uid, mail_group_id=None, **post):
        blog_id = request.registry['mail.group'].message_post(cr, uid, mail_group_id,
                body=_("Blog content.<br/>Please edit this content then you can publish this blog."),
                subject=_("Blog title"),
                website_published=False,
                type='comment',
                subtype='mt_comment',
                context={'mail_create_nosubscribe': True},
            )
        return werkzeug.utils.redirect("/blog/%s/%s" % (mail_group_id, blog_id))
