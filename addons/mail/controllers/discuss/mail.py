from odoo.http import request
from odoo.addons.mail.controllers.mail import MailController
from odoo.addons.mail.controllers.discuss.public_page import PublicPageController
from odoo.addons.mail.tools.discuss import Store

class DiscussMailController(MailController):

    def _mail_thread_message_redirect(self, message):
        """Deprecated - use _redirect_to_record instead. """
        if message.model != 'discuss.channel':
            return super()._mail_thread_message_redirect(message)
        if not request.env.user._is_internal():
            thread = request.env[message.model].search([('id', '=', message.res_id)])
            store = Store().add_global_values(isChannelTokenSecret=True)
            store.add(thread, {"highlightMessage": message.id})
            return PublicPageController()._response_discuss_channel_invitation(store, thread)
        return request.redirect(f'/odoo/action-mail.action_discuss?active_id={message.res_id}&highlight_message_id={message.id}')
