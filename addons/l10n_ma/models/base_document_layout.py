# Part of Odoo. See LICENSE file for full copyright and licensing details.
from markupsafe import Markup

from odoo import api, fields, models


class BaseDocumentLayout(models.TransientModel):
    _inherit = 'base.document.layout'

    @api.model
    def _default_company_details(self):
        # OVERRIDE web/models/base_document_layout
        company_details = super()._default_company_details()
        if self.env.company.country_code == 'MA':
            company_details += Markup('<br> ICE: %s') % self.env.company.company_registry
        return company_details

    company_details = fields.Html(default=_default_company_details)
