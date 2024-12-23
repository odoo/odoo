# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import NotFound, Forbidden

from odoo import http
from odoo.http import request
from odoo.addons.mail.controllers.thread import ThreadController
from odoo.addons.portal.controllers.portal_thread import PortalChatter
from odoo.tools import plaintext2html, html2plaintext


class SlidesPortalChatter(PortalChatter):

    def _portal_post_has_content(self, thread_model, thread_id, message, attachment_ids=None, **kw):
        """ Relax constraint on slide model: having a rating value is sufficient
        to consider we have a content. """
        if thread_model == 'slide.channel' and kw.get('rating_value'):
            return True
        return super()._portal_post_has_content(thread_model, thread_id, message, attachment_ids=attachment_ids, **kw)

    @http.route([
        '/slides/mail/update_comment',
        ], type='jsonrpc', auth="user", methods=['POST'])
    def mail_update_message(self, thread_model, thread_id, message_id, post_data, **post):
        # keep this mechanism intern to slide currently (saas 12.5) as it is
        # considered experimental
        if thread_model != 'slide.channel':
            raise Forbidden()
        thread_id = int(thread_id)
        attachment_ids = post_data.get('attachment_ids', [])

        self._portal_post_check_attachments(attachment_ids, post.get('attachment_tokens', []))

        channel = ThreadController._get_thread_with_access(
            "slide.channel", thread_id,
            # TDE todo: should rely on '_get_mail_message_access'
            mode=request.env["slide.channel"]._mail_post_access,
            pid=int(post.pop('pid', None)) or False,
            **post,
        )
        if not channel:
            raise Forbidden()
        # fetch and update mail.message
        message_id = int(message_id)
        message_body = plaintext2html(post_data.get('body', ''))
        subtype_comment_id = request.env['ir.model.data']._xmlid_to_res_id('mail.mt_comment')
        domain = [
            ('model', '=', thread_model),
            ('res_id', '=', thread_id),
            ('subtype_id', '=', subtype_comment_id),
            ('author_id', '=', request.env.user.partner_id.id),
            ('message_type', '=', 'comment'),
            ('id', '=', message_id)
        ]  # restrict to the given message_id
        message = request.env['mail.message'].search(domain, limit=1)
        if not message:
            raise NotFound()
        message.sudo().write({
            'body': message_body,
            'attachment_ids': [(4, aid) for aid in attachment_ids],
        })

        # update rating
        if post_data.get('rating_value'):
            domain = [('res_model', '=', thread_model), ('res_id', '=', thread_id), ('message_id', '=', message.id)]
            rating = request.env['rating.rating'].sudo().search(domain, order='write_date DESC', limit=1)
            rating.write({
                'rating': float(post_data['rating_value']),
                'feedback': html2plaintext(message.body),
            })
        return {
            'default_message_id': message.id,
            'default_message': html2plaintext(message.body),
            'default_rating_value': message.rating_value,
            'rating_avg': channel.rating_avg,
            'rating_count': channel.rating_count,
            'default_attachment_ids': message.attachment_ids.sudo().read(['id', 'name', 'mimetype', 'file_size', 'access_token']),
            'force_submit_url': '/slides/mail/update_comment',
        }
