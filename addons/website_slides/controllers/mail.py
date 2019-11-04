# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug

from werkzeug.exceptions import NotFound, Forbidden

from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.mail import _check_special_access, PortalChatter
from odoo.tools import plaintext2html


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
        return result

    @http.route([
        '/slides/mail/update_comment',
        '/mail/chatter_update',
        ], type='http', auth="user")
    def mail_update_message(self, res_model, res_id, message, message_id, redirect=None, attachment_ids='', attachment_tokens='', **post):
        # keep this mecanism intern to slide currently (saas 12.5) as it is
        # considered experimental
        if res_model != 'slide.channel':
            raise Forbidden()
        res_id = int(res_id)

        attachment_ids = [int(attachment_id) for attachment_id in attachment_ids.split(',') if attachment_id]
        attachment_tokens = [attachment_token for attachment_token in attachment_tokens.split(',') if attachment_token]
        self._portal_post_check_attachments(attachment_ids, attachment_tokens)

        pid = int(post['pid']) if post.get('pid') else False
        if not _check_special_access(res_model, res_id, token=post.get('token'), _hash=post.get('hash'), pid=pid):
            raise Forbidden()

        # fetch and update mail.message
        message_id = int(message_id)
        message_body = plaintext2html(message)
        domain = [
            ('model', '=', res_model),
            ('res_id', '=', res_id),
            ('is_internal', '=', False),
            ('author_id', '=', request.env.user.partner_id.id),
            ('message_type', '=', 'comment'),
            ('id', '=', message_id)
        ]  # restrict to the given message_id
        message = request.env['mail.message'].search(domain, limit=1)
        if not message:
            raise NotFound()
        message.write({
            'body': message_body,
            'attachment_ids': [(4, aid) for aid in attachment_ids],
        })

        # update rating
        if post.get('rating_value'):
            domain = [('res_model', '=', res_model), ('res_id', '=', res_id), ('is_internal', '=', False), ('message_id', '=', message.id)]
            rating = request.env['rating.rating'].sudo().search(domain, order='write_date DESC', limit=1)
            rating.write({
                'rating': float(post['rating_value'])
            })

        # redirect to specified or referrer or simply channel page as fallback
        redirect_url = redirect or (request.httprequest.referrer and request.httprequest.referrer + '#review') or '/slides/%s' % res_id
        return werkzeug.utils.redirect(redirect_url, 302)
