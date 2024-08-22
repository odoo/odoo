# Part of Odoo. See LICENSE file for full copyright and licensing details.

import uuid
from markupsafe import Markup

from odoo import models
from odoo.addons.mail.tools.discuss import Store


class BusListenerMixin(models.AbstractModel):
    _inherit = "bus.listener.mixin"

    def _bus_send_transient_message(self, channel, content):
        """Posts a fake message in the given ``channel``, only visible for ``self`` listeners."""
        message_id = uuid.uuid4()
        self._bus_send_store(
            Store(
                "mail.message",
                {
                    "author": Store.one(self.env.ref("base.partner_root"), only_id=True),
                    "body": Markup("<span class='o_mail_notification'>%s</span>") % content,
                    "id": message_id,
                    "is_note": True,
                    "is_transient": True,
                    "thread": Store.one(channel, only_id=True),
                },
            ).add(
                channel,
                {"messages": [("ADD", [message_id])], "transientMessages": [("ADD", [message_id])]},
                as_thread=True,
            )
        )
