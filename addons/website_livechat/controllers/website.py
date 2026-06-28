from odoo import http
from odoo.http import request
from odoo.addons.im_livechat.tools.misc import force_guest_env
from odoo.addons.website.controllers.main import Website


class WebsiteLivechat(Website):

    @http.route()
    def track(self, res_model, res_id, **kwargs):
        # Since _upsert_visitor needs the guest in the context
        guest_token = request.httprequest.cookies.get(request.env['mail.guest']._cookie_name)
        if guest_token:
            force_guest_env(guest_token)
        return super().track(res_model=res_model, res_id=res_id, **kwargs)
