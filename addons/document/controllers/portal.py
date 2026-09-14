from typing import Any

from odoo.exceptions import AccessError
from odoo.http import request
from odoo.libs.debug_log import DebugLog

from odoo.addons.portal.controllers.portal import CustomerPortal

_debug = DebugLog(__name__)


class DocumentCustomerPortal(CustomerPortal):
    def _prepare_home_portal_values(self, counters: Any) -> dict:
        values = super()._prepare_home_portal_values(counters)
        if "document_count" in counters:
            Document = request.env["document.document"]
            try:
                count = Document.search_count([])
            except AccessError:
                _debug.logic("portal_count_denied", user=request.env.user)
                count = 0
            values["document_count"] = count
        return values
