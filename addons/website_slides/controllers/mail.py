# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from odoo.http import request
import werkzeug
from werkzeug.exceptions import NotFound, Forbidden

from odoo import http
from odoo.addons.portal.controllers.mail import _check_special_access
from odoo.tools import plaintext2html

_logger = logging.getLogger(__name__)


class SlidesMail(http.Controller):

    @http.route('/slides/mail/update_comment', type='http', auth="user")
    def mail_update_message(self, res_id, message, message_id, **post):

        res_model = 'slide.channel'  # keep this mecanism intern to slide
        message_body = plaintext2html(message)
        res_id = int(res_id)
        message_id = int(message_id)
        pid = int(post['pid']) if post.get('pid') else False

        if not _check_special_access(res_model, res_id, token=post.get('token'), _hash=post.get('hash'), pid=pid):
            raise Forbidden()

        # update mail.message
        domain = [
            ('model', '=', res_model),
            ('res_id', '=', res_id),
            ('website_published', '=', True),
            ('author_id', '=', request.env.user.partner_id.id),
            ('message_type', '=', 'comment'),
            ('id', '=', message_id)
        ]  # restrict to the given message_id
        message = request.env['mail.message'].search(domain, limit=1)
        if not message:
            raise NotFound()
        message.write({
            'body': message_body
        })

        # update rating
        if post.get('rating_value'):
            domain = [('res_model', '=', res_model), ('res_id', '=', res_id), ('website_published', '=', True), ('message_id', '=', message.id)]
            rating = request.env['rating.rating'].search(domain, order='write_date DESC', limit=1)
            rating.write({
                'rating': float(post['rating_value'])
            })

        return werkzeug.utils.redirect(request.httprequest.referrer, 302)
