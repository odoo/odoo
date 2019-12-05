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
    @route('/mail/chat_post', type="json", auth="public", cors="*")
    def mail_chat_post(self, uuid, message_content, **kwargs):
        mail_channel = request.env["mail.channel"].sudo().search([('uuid', '=', uuid)], limit=1)
        if not mail_channel:
            return False

        # find the author from the user session
        if request.session.uid:
            author = request.env['res.users'].sudo().browse(request.session.uid).partner_id
            author_id = author.id
            email_from = author.email_formatted
        else:  # If Public User, use catchall email from company
            author_id = False
            email_from = mail_channel.anonymous_name or mail_channel.create_uid.company_id.catchall_formatted
        # post a message without adding followers to the channel. email_from=False avoid to get author from email data
        body = tools.plaintext2html(message_content)
        message = mail_channel.with_context(mail_create_nosubscribe=True).message_post(author_id=author_id,
                                                                                       email_from=email_from, body=body,
                                                                                       message_type='comment',
                                                                                       subtype_xmlid='mail.mt_comment')
        return message and message.id or False

    @route(['/mail/chat_history'], type="json", auth="public", cors="*")
    def mail_chat_history(self, uuid, last_id=False, limit=20):
        channel = request.env["mail.channel"].sudo().search([('uuid', '=', uuid)], limit=1)
        if not channel:
            return []
        else:
            return channel.channel_fetch_message(last_id, limit)
