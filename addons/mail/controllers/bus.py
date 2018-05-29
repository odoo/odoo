# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import SUPERUSER_ID, tools
from odoo.http import request, route
from odoo.addons.bus.controllers.main import BusController


class MailChatController(BusController):

    def _default_request_uid(self):
        """ For Anonymous people, they receive the access right of SUPERUSER_ID since they have NO access (auth=none)
            !!! Each time a method from this controller is call, there is a check if the user (who can be anonymous and Sudo access)
            can access to the resource.
        """
        return request.session.uid and request.session.uid or SUPERUSER_ID

    # --------------------------
    # Extends BUS Controller Poll
    # --------------------------
    def _poll(self, dbname, channels, last, options):
        if request.session.uid:
            partner_id = request.env.user.partner_id.id

            if partner_id:
                channels = list(channels)       # do not alter original list
                for mail_channel in request.env['mail.channel'].search([('channel_partner_ids', 'in', [partner_id])]):
                    channels.append((request.db, 'mail.channel', mail_channel.id))
                # personal and needaction channel
                channels.append((request.db, 'res.partner', partner_id))
                channels.append((request.db, 'ir.needaction', partner_id))
        return super(MailChatController, self)._poll(dbname, channels, last, options)

    # --------------------------
    # Anonymous routes (Common Methods)
    # --------------------------
    @route('/mail/chat_post', type="json", auth="none")
    def mail_chat_post(self, uuid, message_content, **kwargs):
        # find the author from the user session, which can be None
        author_id = False  # message_post accept 'False' author_id, but not 'None'
        if request.session.uid:
            author_id = request.env['res.users'].sudo().browse(request.session.uid).partner_id.id
        # post a message without adding followers to the channel. email_from=False avoid to get author from email data
        mail_channel = request.env["mail.channel"].sudo().search([('uuid', '=', uuid)], limit=1)
        body = tools.plaintext2html(message_content)
        message = mail_channel.sudo().with_context(mail_create_nosubscribe=True).message_post(author_id=author_id, email_from=False, body=body, message_type='comment', subtype='mail.mt_comment')
        return message and message.id or False

    @route(['/mail/chat_history'], type="json", auth="none")
    def mail_chat_history(self, uuid, last_id=False, limit=20):
        channel = request.env["mail.channel"].sudo().search([('uuid', '=', uuid)], limit=1)
        if not channel:
            return []
        else:
            return channel.channel_fetch_message(last_id, limit)
