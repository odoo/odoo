from odoo import http
from odoo.http import request


class OdxOwlController(http.Controller):

    @http.route("/odx_owl/showcase/hr-dashboard", type="http", auth="user", website=True)
    def showcase_hr_dashboard(self, **kwargs):
        return request.render("odx_owl.showcase_hr_dashboard")

    @http.route("/odx_owl/showcase/onboarding", type="http", auth="user", website=True)
    def showcase_onboarding(self, **kwargs):
        return request.render("odx_owl.showcase_onboarding")
