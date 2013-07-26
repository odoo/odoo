# -*- coding: utf-8 -*-

import openerp
from openerp.addons.web.http import request
from openerp.addons.website import website
import werkzeug


class website_mail(website):

    @website.route(['/blog', '/blog/<int:mail_group_id>', '/blog/<int:mail_group_id>/<int:blog_id>'], type='http', auth="admin")
    def blog(self, cr, uid, mail_group_id=None, blog_id=None, **post):
        mail_group_obj = request.registry['mail.group']
        message_obj = request.registry['mail.message']

        domain = [("subject", "!=", False), ("parent_id", "=", False)]

        if blog_id and not message_obj.search(cr, uid, [("id", "=", blog_id)] + domain):
            blog_id = None
        else:
            blog_domain = [("parent_id", "=", blog_id)]

        domain += [("id", "in", message_obj.search(cr, uid,
            mail_group_id and [("res_id", "=", mail_group_id), ("model", "=", 'mail.group')] or [("model", "=", 'mail.group')]))]

        values = {
            'res_company': request.registry['res.company'].browse(cr, uid, 1),
            'blog_ids': not blog_id and message_obj.browse(cr, uid,
                    message_obj.search(cr, uid, domain, order="create_date desc", limit=20)) or None,
            'popular_ids': message_obj.browse(cr, uid,
                    message_obj.search(cr, uid, domain, order="child_ids desc", limit=5)),
            'recent_ids': message_obj.browse(cr, uid,
                    message_obj.search(cr, uid, domain, order="create_date desc", limit=5)),
            'last_ids': message_obj.browse(cr, uid,
                    message_obj.search(cr, uid, domain, order="write_date desc", limit=5)),
            'blog_id': blog_id and message_obj.browse(cr, uid, blog_id) or None,
            'blog_message_ids': blog_id and message_obj.browse(cr, uid,
                    message_obj.search(cr, uid, blog_domain, order="create_date asc", limit=20)) or None,
        }
        html = self.render(cr, uid, "website_mail.index", values)
        return html

    @website.route(['/blog/publish'], type='http', auth="admin")
    def publish(self, cr, uid, **post):
        message_id = int(post['message_id'])
        message_obj = request.registry['mail.message']

        blog = message_obj.browse(cr, uid, message_id)
        message_obj.write(cr, uid, [message_id], {'website_published': not blog.website_published})
        blog = message_obj.browse(cr, uid, message_id)

        return blog.website_published and "1" or "0"

    @website.route(['/blog/<int:mail_group_id>/<int:blog_id>/post'], type='http', auth="admin")
    def message_post(self, cr, uid, mail_group_id=None, blog_id=None, **post):
        if post.get('body') and post.get('name') and post.get('email') and post.get('email').index('@') > 0:
            if self.isloggued():
                author_id = request.registry['res.users'].browse(cr, uid, uid).partner_id.id
            else:
                partner_obj = request.registry['res.partner']
                partner_ids = partner_obj.search(cr, uid, [('name', '=', post.get('name')), ('email', '=', post.get('email'))])
                if partner_ids:
                    author_id = partner_ids[0]
                else:
                    author_id = partner_obj.create(cr, openerp.SUPERUSER_ID, {'name': post.get('name'), 'email': post.get('email')})

            request.registry['mail.group'].message_post(cr, uid, mail_group_id,
                    body=post.get('body'),
                    parent_id=blog_id,
                    author_id=author_id,
                    website_published= blog_id and True or False
                )

        return werkzeug.utils.redirect("/blog/%s/%s" % (mail_group_id, blog_id))
