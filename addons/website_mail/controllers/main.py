# -*- coding: utf-8 -*-

from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website.controllers.main import template_values


class website_mail(http.Controller):

    @http.route(['/blog', '/blog/<int:mail_group_id>/<int:blog_id>'], type='http', auth="admin")
    def blog(self, mail_group_id=None, blog_id=None, **post):
        cr = request.cr
        uid = request.uid
        values = template_values()

        mail_group_obj = request.registry['mail.group']
        mail_message_obj = request.registry['mail.message']

        if not mail_group_id:
            mail_group_ids = mail_group_obj.search(cr, uid, [("public", "=", "public")])
            mail_group_id = mail_group_ids[0]

        domain = [("subject", "!=", False), ("parent_id", "=", False)]#, ("website_published", "=", True)]

        if blog_id and not mail_message_obj.search(cr, uid, [("id", "=", blog_id)] + domain):
            blog_id = None

        message_ids = mail_message_obj.search(cr, uid, [("res_id", "=", mail_group_id), ("model", "=", 'mail.group')])
        domain += [("id", "in", message_ids)]

        values.update({
            'res_company': request.registry['res.company'].browse(cr, uid, 1),
            'blog_ids': not blog_id and mail_message_obj.browse(cr, uid,
                    mail_message_obj.search(cr, uid, domain, order="create_date desc", limit=20)) or None,
            'popular_ids': mail_message_obj.browse(cr, uid,
                    mail_message_obj.search(cr, uid, domain, order="child_ids desc", limit=5)),
            'recent_ids': mail_message_obj.browse(cr, uid,
                    mail_message_obj.search(cr, uid, domain, order="create_date desc", limit=5)),
            'last_ids': mail_message_obj.browse(cr, uid,
                    mail_message_obj.search(cr, uid, domain, order="write_date desc", limit=5)),
            'blog_id': blog_id and mail_message_obj.browse(cr, uid, blog_id) or None,
        })
        html = request.registry.get("ir.ui.view").render(cr, uid, "website_mail.index", values)
        return html
