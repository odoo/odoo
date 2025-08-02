from odoo import http
from odoo.http import request


class WebsiteQuoteController(http.Controller):
    @http.route(["/my_quote"], type="http", auth="public")
    def show_quote(self, **kwargs):
        quote = "The best way to get started is to quit talking and begin doing."
        return request.render(
            "website_quote.template_my_quote",
            {
                "quote": quote,
            },
        )
