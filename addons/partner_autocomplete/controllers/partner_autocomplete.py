from odoo import http
from odoo.http import request
import requests


class PartnerAutocompleteController(http.Controller):

    @http.route("/partner_autocomplete", auth="user", type="http", methods=["GET"])
    def partner_autocomplete_internal(self, query=None):
        """Requests clearbit from backend instead of frontend to circumvent adblockers"""
        response = requests.get(
            "https://autocomplete.clearbit.com/v1/companies/suggest", timeout=10, params={'query': query}
        )
        return request.make_response(response.text, headers={"Content-Type": "application/json; charset=utf-8"})
