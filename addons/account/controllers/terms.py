from odoo import _, http
from odoo.http import request
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


def sitemap_terms(env, rule, qs):
    if qs and qs.lower() not in "/terms":
        return
    use_invoice_terms = (
        env["ir.config_parameter"].sudo().get_param("account.use_invoice_terms")
    )
    if use_invoice_terms and env.company.terms_type == "html":
        yield {"loc": "/terms"}


class TermsController(http.Controller):
    @http.route(
        "/terms", type="http", auth="public", website=True, sitemap=sitemap_terms
    )
    def terms_conditions(self, **kwargs):
        _debug.pipeline("route", handler="TermsController.terms_conditions")
        use_invoice_terms = (
            request.env["ir.config_parameter"]
            .sudo()
            .get_param("account.use_invoice_terms")
        )
        if not (use_invoice_terms and request.env.company.terms_type == "html"):
            return request.render(
                "http_routing.http_error",
                {
                    "status_code": _("Oops"),
                    "status_message": _(
                        """The requested page is invalid, or doesn't exist anymore."""
                    ),
                },
            )
        values = {
            "use_invoice_terms": use_invoice_terms,
            "company": request.env.company,
        }
        return request.render("account.account_terms_conditions_page", values)
