from odoo import http
from odoo.http import request
import requests


class PartnerAutocompleteController(http.Controller):

    @http.route("/partner_autocomplete", auth="user", type="http", methods=["GET"])
    def partner_autocomplete_internal(self, query=None):
        """Requests clearbit from backend instead of frontend to circumvent adblockers"""
        clearbit_url = f"https://autocomplete.clearbit.com/v1/companies/suggest?query={query}"
        response = requests.get(clearbit_url)
        return request.make_json_response(response.json())
