# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.mail import PortalChatter


class BlogPortalChatter(PortalChatter):

    @http.route(['/mail/chatter_post'], type='http', methods=['POST'], auth='public', website=True)
    def portal_chatter_post(self, res_model, res_id, message, redirect=None, attachment_ids='', attachment_tokens='', **kw):
        """Create a new `mail.message` with the given `message` and/or
        `attachment_ids` and redirect the user to the newly created message.

        The message will be associated to the record `res_id` of the model
        `res_model`. The user must have access rights on this target document or
        must provide valid identifiers through `kw`. See `_message_post_helper`.
        """
        blog_post = None
        if res_model == 'blog.post' and res_id:
            blog_post = request.env['blog.post'].browse(int(res_id)).exists()
        if not blog_post:
            return super(BlogPortalChatter, self).portal_chatter_post(
                res_model, res_id, message,
                redirect=redirect,
                attachment_ids=attachment_ids,
                attachment_tokens=attachment_tokens,
                **kw)
        else:
            attachment_ids = [int(attachment_id) for attachment_id in attachment_ids.split(',') if attachment_id]
            attachment_tokens = [attachment_token for attachment_token in attachment_tokens.split(',') if attachment_token]
            self._portal_post_check_attachments(attachment_ids, attachment_tokens)
            url = super(BlogPortalChatter, self).portal_chatter_post(
                res_model, res_id, message,
                redirect=redirect,
                attachment_ids='',
                attachment_tokens='',
                **kw)
            last_message = blog_post.message_ids[-1]
            if last_message:
                last_message.sudo().write({
                    'attachment_ids': attachment_ids
                })
            return url
