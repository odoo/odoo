from odoo.http import request

from odoo.addons.google_address_autocomplete.controllers.google_address_autocomplete import AutoCompleteController

class WebsiteSaleAutoCompleteController(AutoCompleteController):
    def _get_api_key(self, use_employees_key):
        if not use_employees_key:
            return request.env['website'].get_current_website().sudo().google_places_api_key
        return super()._get_api_key(use_employees_key)

    def _use_places_api_new(self, use_employees_key):
        if not use_employees_key:
            return request.env['website'].get_current_website()._google_places_use_api_new()
        return super()._use_places_api_new(use_employees_key)
