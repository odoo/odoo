# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo import models, _


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _notify_thread(self, message, msg_vals=False, **kwargs):
        rdata = super()._notify_thread(message, msg_vals, **kwargs)
        self._notify_mentioned_channel(message, **kwargs)
        return rdata

    def _notify_mentioned_channel(self, message, channel_ids=None, **kwargs):
        """ Notify channels that have been mentioned in message"""
        if channel_ids and self._name != "discuss.channel":
            body = Markup(_("This channel was mentioned in %s")) % (
                Markup('<a href="/mail/message/%s" data-oe-type="notification">%s</a>') % (
                    message.id, self.display_name
                )
            )
            for channel in self.env['discuss.channel'].browse(channel_ids):
                channel.message_post(body=body, message_type="notification", subtype_xmlid="mail.mt_comment")

    def _get_allowed_message_post_params(self):
        return super()._get_allowed_message_post_params() | {"channel_ids"}

    def _get_notify_valid_parameters(self):
        return super()._get_notify_valid_parameters() | {"channel_ids"}
