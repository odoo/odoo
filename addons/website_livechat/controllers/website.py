from odoo import http
from odoo.http import request

from odoo.addons.website.controllers.main import Website


class WebsiteLivechat(Website):

    @http.route()
    def track(self, res_model, res_id, **kwargs):
        # Since _upsert_visitor needs the guest in the context
        guest_token = request.httprequest.cookies.get(request.env['mail.guest']._cookie_name)
        if guest_token and request.env.user._is_public():
            if guest := request.env['mail.guest']._get_guest_from_token(guest_token):
                request.update_context(guest=guest)
        return super().track(res_model=res_model, res_id=res_id, **kwargs)
