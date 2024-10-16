from odoo import models
from odoo.addons import web


class IrHttp(web.IrHttp):

    def session_info(self):
        result = super().session_info()
        result["tour_enabled"] = self.env.user.tour_enabled
        result['current_tour'] = self.env["web_tour.tour"].get_current_tour()
        return result
