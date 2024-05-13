# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.controllers import thread
from odoo.addons.portal.models.mail_thread import check_portal_access
from odoo import _, http
from odoo.http import request
from odoo.tools import html2plaintext
from odoo.exceptions import ValidationError


class ThreadController(thread.ThreadController):

    @http.route()
    @check_portal_access
    def mail_message_update_content(
            self,
            message_id,
            body,
            attachment_ids,
            attachment_tokens=None,
            partner_ids=None,
            **kwargs
    ):
        message = super().mail_message_update_content(
            message_id, body, attachment_ids, attachment_tokens, partner_ids, **kwargs
        )
        if kwargs.get('rating_value'):
            domain = [('message_id', '=', message_id)]
            rating = request.env['rating.rating'].sudo().search(domain, order='write_date DESC', limit=1)
            rating.write({
                'rating': float(kwargs['rating_value']),
                'feedback': html2plaintext(body),
            })
            thread = request.env[message['model']].browse(message['res_id'])
            message['rating_value'] = kwargs['rating_value']
            message['rating_avg'] = thread.rating_avg
            message['rating_count'] = thread.rating_count
        return message

    @http.route()
    @check_portal_access
    def mail_message_post(self, thread_model, thread_id, post_data, context=None, **kwargs):
        previous_post = request.env["mail.message"].search([
            ("res_id", "=", thread_id),
            ("author_id", "=", request.env.user.partner_id.id),
            ("model", "=", "slide.channel"),
            ("subtype_id", "=", request.env.ref("mail.mt_comment").id),
        ])
        if thread_model == "slide.channel" and previous_post:
            raise ValidationError(_("Only a single review can be posted per course."))
        message = super().mail_message_post(thread_model, thread_id, post_data, context, **kwargs)
        if post_data.get('rating_value'):
            thread = request.env[thread_model].browse(int(thread_id))
            message['rating_avg'] = thread.rating_avg
            message['rating_count'] = thread.rating_count
        return message
