from odoo import http

from odoo.addons.mail.tools.discuss import add_guest_to_context
from odoo.addons.website.controllers.main import Website


class WebsiteLivechat(Website):
    @http.route()
    @add_guest_to_context  # _upsert_visitor needs the guest in the context
    def track(self, res_model, res_id, **kwargs):
        return super().track(res_model=res_model, res_id=res_id, **kwargs)
