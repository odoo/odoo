# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


class MailBot(models.AbstractModel):
    _inherit = 'mail.bot'

    def _get_answer(self, record, body, values, command):
        if self._is_bot_in_private_channel(record):
            if self._is_bot_pinged(values):
                return _("That's me! 🎉<br/>Try to type \":\" to use canned responses.")
            elif values.get("canned_response_ids"):
                discuss_href = 'href="/web#action=mail.mail_channel_action_client_chat&active_id=%s"' % record.id
                discuss_src = 'src="/mail_bot/static/img/odoobot_discuss.png"'
                chatter_src = 'src="/mail_bot/static/img/odoobot_chatter.png"'
                return _("Good, you can customize your canned responses in the live chat application. <br/><br/>") + \
                    _("There are 3 different ways in Odoo to interact with your colleagues: <br/>\
-via this chat window<br/>\
-via the <a href=%s>Discuss</a> application:<br/><img %s/><br/><br/>\
-or via the chatter:<br/><img %s/><br/><br/>\
Aaaaand that's it! Enjoy discovering Odoo!") % (discuss_href, discuss_src, chatter_src)

        return super(MailBot, self)._get_answer(record, body, values, command)
