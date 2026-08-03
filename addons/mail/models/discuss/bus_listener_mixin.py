# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo import models

from odoo.addons.base.models.ir_sequence import _select_nextval
from odoo.addons.mail.tools.discuss import Store


class BusListenerMixin(models.AbstractModel):
    _inherit = "bus.listener.mixin"

    def _bus_send_transient_message(self, channel, content):
        """Posts a fake message in the given ``channel``, only visible for ``self`` listeners."""
        message_id = _select_nextval(self.env.cr, "mail_message_id_seq")[0]
        store = Store(bus_channel=self)
        store.add_model_values(
            "mail.message",
            lambda res: (
                res.one("author_id", [], value=self.env.ref("base.partner_root")),
                res.attr("body", Markup("<span class='o_mail_notification'>%s</span>") % content),
                res.attr("id", message_id),
                res.attr("is_transient", True),
                res.attr("subtype_id", self.env["ir.model.data"]._xmlid_to_res_id("mail.mt_note")),
                res.one("thread", [], as_thread=True, value=channel),
            ),
        )
        store.add(
            channel,
            lambda res: (
                res.many("messages", [], value=[message_id], mode="ADD"),
                res.many("transientMessages", [], value=[message_id], mode="ADD"),
            ),
            as_thread=True,
        )
