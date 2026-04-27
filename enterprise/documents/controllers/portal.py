# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.exceptions import AccessError
from odoo.http import request


class DocumentCustomerPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'document_count' in counters:
            Document = request.env['documents.document']
            try:
                count = Document.search_count([])
            except AccessError:
                count = 0
            values['document_count'] = count
        return values
