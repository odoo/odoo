# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.urls import url_encode

from odoo.http import request
from odoo.addons.mail.controllers import mail


class MailController(mail.MailController):

    @classmethod
    def _redirect_to_record(cls, model, res_id, access_token=None, **kwargs):
        if (
            model and res_id and model in request.env and
            isinstance(request.env[model], request.env.registry["product.template"]) and
            request.env.user.is_public
        ):
            url_params = {"highlight_message_id": kwargs.get("highlight_message_id")}
            url = f"/shop/{res_id}?{url_encode(url_params)}"
            return request.redirect(url)
        return super()._redirect_to_record(model, res_id, access_token=access_token, **kwargs)
