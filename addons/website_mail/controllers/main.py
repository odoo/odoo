# -*- coding: utf-8 -*-

import openerp
from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website.controllers.main import template_values
from openerp.osv import osv, orm
import werkzeug


class website_mail(http.Controller):

    def get_editable(self, blog_id):
        try:
            request.session.check_security()
            uid = request.session._uid

            mail_group_obj = request.registry['mail.group']
            mail_group_obj.check_access_rights(request.cr, uid, 'write')
            mail_group_obj.check_access_rule(request.cr, uid, [blog_id], 'write', context=context)
            editable = True
        except (http.SessionExpiredException, osv.except_osv, orm.except_orm):
            editable = False

        return editable

    @http.route(['/blog', '/blog/<int:mail_group_id>/<int:blog_id>'], type='http', auth="admin")
    def blog(self, mail_group_id=None, blog_id=None, **post):
        cr = request.cr
        uid = request.uid
        values = template_values()

        mail_group_obj = request.registry['mail.group']
        message_obj = request.registry['mail.message']

        if not mail_group_id:
            mail_group_ids = mail_group_obj.search(cr, uid, [("public", "=", "public")])
            mail_group_id = mail_group_ids[0]

        domain = [("subject", "!=", False), ("parent_id", "=", False)]

        editable = self.get_editable(blog_id)
        if not editable:
            domain += [("website_published", "=", True)]

        if blog_id and not message_obj.search(cr, uid, [("id", "=", blog_id)] + domain):
            blog_id = None
        else:
            blog_domain = [("parent_id", "=", blog_id)]
            if not editable:
                blog_domain += [("website_published", "=", True)]

        message_ids = message_obj.search(cr, uid, [("res_id", "=", mail_group_id), ("model", "=", 'mail.group')])
        domain += [("id", "in", message_ids)]

        values.update({
            'blog_editable': editable,
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
        })
        html = request.registry.get("ir.ui.view").render(cr, uid, "website_mail.index", values)
        return html

    @http.route(['/blog/publish'], type='http', auth="admin")
    def publish(self, **post):
        cr = request.cr
        uid = request.uid
        message_id = int(post['message_id'])
        message_obj = request.registry['mail.message']

        blog = message_obj.browse(cr, openerp.SUPERUSER_ID, message_id)
        website_published = blog.website_published
        if self.get_editable(message_id):
            website_published = not website_published
            message_obj.write(cr, uid, [message_id], {'website_published': website_published})

        return website_published and "1" or "0"

    @http.route(['/blog/<int:mail_group_id>/<int:blog_id>/post'], type='http', auth="admin")
    def message_post(self, mail_group_id=None, blog_id=None, **post):
        message_obj = request.registry['mail.message']
        partner_obj = request.registry['res.partner']
        blog = message_obj.browse(request.cr, request.uid, blog_id)

        if blog.website_published and post.get('body') and post.get('name') and post.get('email') and post.get('email').index('@') > 0:
            partner_ids = partner_obj.search(request.cr, request.uid, [('email', '=', post.get('email'))])
            if partner_ids:
                author_id = partner_ids[0]
            else:
                author_id = partner_obj.create(request.cr, request.uid, {'name': post.get('name'), 'email': post.get('email')})

            values = {
                'body': post.get('body'),
                'parent_id': blog.id,
                'author_id': author_id,
                'website_published': True,
            }
            message_obj.create(request.cr, request.uid, values)

        return werkzeug.utils.redirect("/blog/%s/%s" % (mail_group_id, blog_id))
