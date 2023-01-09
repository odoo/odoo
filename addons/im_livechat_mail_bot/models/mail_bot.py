# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


class MailBot(models.AbstractModel):
    _inherit = 'mail.bot'

    def _get_answer(self, record, body, values, command):
        odoobot_state = self.env.user.odoobot_state
        if self._is_bot_in_private_channel(record):
            if odoobot_state == "onboarding_attachement" and values.get("attachment_ids"):
                self.env.user.odoobot_failed = False
                self.env.user.odoobot_state = "onboarding_canned"
                return _("That's me! 🎉<br/>Try typing <span class=\"o_odoobot_command\">:</span> to use canned responses.")
            elif odoobot_state == "onboarding_canned" and values.get("canned_response_ids"):
                self.env.user.odoobot_failed = False
                self.env.user.odoobot_state = "idle"
                return _("Good, you can customize canned responses in the live chat application.<br/><br/><b>It's the end of this overview</b>, enjoy discovering Odoo!")
            # repeat question if needed
            elif odoobot_state == 'onboarding_canned' and not self._is_help_requested(body):
                self.env.user.odoobot_failed = True
                return _("Not sure what you are doing. Please, type <span class=\"o_odoobot_command\">:</span> and wait for the propositions. Select one of them and press enter.")
        return super(MailBot, self)._get_answer(record, body, values, command)
