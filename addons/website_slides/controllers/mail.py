# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug

from werkzeug.exceptions import NotFound, Forbidden

from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.mail import _check_special_access, PortalChatter
from odoo.tools import plaintext2html, html2plaintext


class SlidesPortalChatter(PortalChatter):

    @http.route(['/mail/chatter_post'], type='json', methods=['POST'], auth='public', website=True)
    def portal_chatter_post(self, res_model, res_id, message, **kw):
        result = super(SlidesPortalChatter, self).portal_chatter_post(res_model, res_id, message, **kw)
        if res_model == 'slide.channel':
            rating_value = kw.get('rating_value', False)
            slide_channel = request.env[res_model].sudo().browse(int(res_id))
            if rating_value and slide_channel and request.env.user.partner_id.id == int(kw.get('pid')):
                # apply karma gain rule only once
                request.env.user.add_karma(slide_channel.karma_gen_channel_rank)
            result.update({
                'default_rating_value': rating_value,
                'rating_avg': slide_channel.rating_avg,
                'rating_count': slide_channel.rating_count,
                'force_submit_url': result.get('default_message_id') and '/slides/mail/update_comment',
            })
        return result

    @http.route([
        '/slides/mail/update_comment',
        '/mail/chatter_update',
        ], type='json', auth="user", methods=['POST'])
    def mail_update_message(self, res_model, res_id, message, message_id, attachment_ids=None, attachment_tokens=None, **post):
        # keep this mechanism intern to slide currently (saas 12.5) as it is
        # considered experimental
        if res_model != 'slide.channel':
            raise Forbidden()
        res_id = int(res_id)

        self._portal_post_check_attachments(attachment_ids, attachment_tokens)

        pid = int(post['pid']) if post.get('pid') else False
        if not _check_special_access(res_model, res_id, token=post.get('token'), _hash=post.get('hash'), pid=pid):
            raise Forbidden()

        # fetch and update mail.message
        message_id = int(message_id)
        message_body = plaintext2html(message)
        subtype_comment_id = request.env['ir.model.data']._xmlid_to_res_id('mail.mt_comment')
        domain = [
            ('model', '=', res_model),
            ('res_id', '=', res_id),
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
        if post.get('rating_value'):
            domain = [('res_model', '=', res_model), ('res_id', '=', res_id), ('message_id', '=', message.id)]
            rating = request.env['rating.rating'].sudo().search(domain, order='write_date DESC', limit=1)
            rating.write({
                'rating': float(post['rating_value']),
                'feedback': html2plaintext(message.body),
            })
        channel = request.env[res_model].browse(res_id)
        return {
            'default_message_id': message.id,
            'default_message': html2plaintext(message.body),
            'default_rating_value': message.rating_value,
            'rating_avg': channel.rating_avg,
            'rating_count': channel.rating_count,
            'default_attachment_ids': message.attachment_ids.sudo().read(['id', 'name', 'mimetype', 'file_size', 'access_token']),
            'force_submit_url': '/slides/mail/update_comment',
        }
