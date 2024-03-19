# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request, route
from odoo.addons.mail.controllers.webclient import WebclientController
from odoo.addons.mail.models.discuss.mail_guest import add_guest_to_context


class WebClient(WebclientController):
    def _process_request_for_internal_user(self, store, **kwargs):
        super()._process_request_for_internal_user(store, **kwargs)
        if kwargs.get("livechat_channels"):
            store.add(
                {
                    "LivechatChannel": request.env["im_livechat.channel"].search([]).mapped(
                        lambda c: {
                            "id": c.id,
                            "name": c.name,
                            "hasSelfAsMember": request.env.user in c.user_ids,
                        }
                    )
                }
            )
