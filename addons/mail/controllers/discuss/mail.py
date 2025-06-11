# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug
from urllib.parse import urlencode

from odoo.http import request
from odoo.addons.mail.controllers import mail


class MailController(mail.MailController):

    @classmethod
    def _redirect_to_record(cls, model, res_id, access_token=None, **kwargs):
        if (res_id and model and model == "discuss.channel"):
            if request.env.user._is_internal():
                channel = request.env["discuss.channel"].browse(res_id).exists()
                if not channel or not channel.has_access("read"):
                    raise werkzeug.exceptions.Unauthorized()
                return cls._redirect_to_messaging(
                    channel_id=res_id,
                    highlight_message_id=kwargs.get("highlight_message_id")
                )
            url_params = {}
            if highlight_message_id := kwargs.get("highlight_message_id"):
                url_params["highlight_message_id"] = highlight_message_id
            url = f"/discuss/channel/{res_id}?{urlencode(url_params)}"
            return request.redirect(url)

        return super()._redirect_to_record(model, res_id, access_token=access_token, **kwargs)
