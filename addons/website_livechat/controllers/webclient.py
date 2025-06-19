from odoo import Command
from odoo.http import request
from odoo.addons.mail.controllers.webclient import WebclientController
from odoo.addons.mail.tools.discuss import Store


class WebClient(WebclientController):
    @classmethod
    def _process_request_for_all(self, store: Store, name, params):
        if name == "init_livechat" and (
            chat_request_channel := self._link_visitor_to_livechat(params)
        ):
            store.add(chat_request_channel, extra_fields={"open_chat_window": True})
            chat_request_channel.is_pending_chat_request = False
        super()._process_request_for_all(store, name, params)

    @classmethod
    def _link_visitor_to_livechat(self, livechat_channel_id):
        """ Check if there is an opened chat request for the website livechat
        channel and the current visitor (from request). If so, link the visitor
        to the chat request channel. Channel will then be returned as part of
        the mail store initialization (/mail/data).
        """
        visitor = request.env['website.visitor']._get_visitor_from_request()
        if not visitor:
            return
        # get active chat_request linked to visitor
        chat_request_channel = (
            request.env["discuss.channel"]
            .sudo()
            .search(
                [
                    ("channel_type", "=", "livechat"),
                    ("livechat_visitor_id", "=", visitor.id),
                    ("livechat_channel_id", "=", livechat_channel_id),
                    ("livechat_end_dt", "=", False),
                    ("has_message", "=", True),
                    ("is_pending_chat_request", "=", True),
                ],
                order="create_date desc",
                limit=1,
            )
        )
        if not chat_request_channel or visitor.partner_id:
            return
        current_guest = request.env["mail.guest"]._get_guest_from_context()
        channel_guest_member = chat_request_channel.channel_member_ids.filtered(lambda m: m.guest_id)
        if current_guest and current_guest != channel_guest_member.guest_id:
            # Channel was created with a guest but the visitor was
            # linked to another guest in the meantime. We need to
            # update the channel to link it to the current guest.
            chat_request_channel.write(
                {
                    "channel_member_ids": [
                        Command.unlink(channel_guest_member.id),
                        Command.create({"guest_id": current_guest.id}),
                    ]
                }
            )
        if not current_guest and channel_guest_member:
            channel_guest_member.guest_id._set_auth_cookie()
        return chat_request_channel
