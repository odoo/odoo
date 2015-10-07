# -*- coding: utf-8 -*
import base64
import openerp

from openerp import SUPERUSER_ID
from openerp.http import request


class MailChatController(openerp.addons.bus.controllers.main.BusController):

    def _default_request_uid(self):
        """ For Anonymous people, they receive the access right of SUPERUSER_ID since they have NO access (auth=none)
            !!! Each time a method from this controller is call, there is a check if the user (who can be anonymous and Sudo access)
            can access to the ressource.
        """
        return request.session.uid and request.session.uid or SUPERUSER_ID

    # --------------------------
    # Extends BUS Controller Poll
    # --------------------------
    def _poll(self, dbname, channels, last, options):
        if request.session.uid:
            partner_id = request.env.user.partner_id.id

            if partner_id:
                for mail_channel in request.env['mail.channel'].search([('channel_partner_ids', 'in', [partner_id])]):
                    channels.append((request.db, 'mail.channel', mail_channel.id))
                # personal and needaction channel
                channels.append((request.db, 'res.partner', partner_id))
                channels.append((request.db, 'ir.needaction', partner_id))
        return super(MailChatController, self)._poll(dbname, channels, last, options)

    # --------------------------
    # Anonymous routes (Common Methods)
    # --------------------------
    @openerp.http.route('/mail/chat_post', type="json", auth="none")
    def mail_chat_post(self, uuid, message_content, **kwargs):
        request_uid = self._default_request_uid()
        # find the author from the user session, which can be None
        author_id = False  # message_post accept 'False' author_id, but not 'None'
        if request.session.uid:
            author_id = request.env['res.users'].sudo().browse(request.session.uid).partner_id.id
        # post a message without adding followers to the channel. email_from=False avoid to get author from email data
        mail_channel = request.env["mail.channel"].sudo(request_uid).search([('uuid', '=', uuid)], limit=1)
        message = mail_channel.sudo(request_uid).with_context(mail_create_nosubscribe=True).message_post(author_id=author_id, email_from=False, body=message_content, message_type='comment', subtype='mail.mt_comment', content_subtype='plaintext', **kwargs)
        return message and message.id or False

    @openerp.http.route(['/mail/chat_history'], type="json", auth="none")
    def mail_chat_history(self, uuid, last_id=False, limit=20):
        request_uid = self._default_request_uid()
        channel = request.env["mail.channel"].sudo(request_uid).search([('uuid', '=', uuid)], limit=1)
        return channel.sudo(request_uid).channel_fetch_message(last_id, limit)

    @openerp.http.route('/mail/chat_init', type="json", auth="none")
    def mail_chat_init(self):
        result = {
            'emoji': request.env['mail.shortcode'].sudo().search_read([('shortcode_type', '=', 'image')], ['source', 'substitution', 'description'])
        }
        # include the previous notifications, only for identified user
        if request.session.uid:
            request_uid = self._default_request_uid()
            result['notifications'] = request.env['mail.channel'].sudo(request_uid).get_init_notifications()
        return result
