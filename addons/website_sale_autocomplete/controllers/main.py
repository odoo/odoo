from odoo.http import request
from odoo.libs.debug_log import DebugLog

from odoo.addons.google_address_autocomplete.controllers.google_address_autocomplete import (
    AutoCompleteController,
)

_debug = DebugLog(__name__)


class WebsiteSaleAutoCompleteController(AutoCompleteController):
    def _get_api_key(self, use_employees_key):
        _debug.logic("autocomplete_api_key_source", employees_key=use_employees_key)
        if not use_employees_key:
            return (
                request.env["website"]
                .get_current_website()
                .sudo()
                .google_places_api_key
            )
        return super()._get_api_key(use_employees_key)
