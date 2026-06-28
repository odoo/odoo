
from odoo.addons.google_address_autocomplete.controllers.google_address_autocomplete import AutoCompleteController


class WebsiteAddressAutoCompleteController(AutoCompleteController):
    def _get_api_key(self, use_employees_key):
        if not use_employees_key:
            return self.env.website.sudo().google_places_api_key
        return super()._get_api_key(use_employees_key)
