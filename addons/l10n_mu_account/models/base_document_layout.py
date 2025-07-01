from markupsafe import Markup

from odoo import api, fields, models


class BaseDocumentLayout(models.TransientModel):
    _inherit = 'base.document.layout'

    @api.model
    def _default_company_details(self):
        company_details = super()._default_company_details()
        company = self.env.company
        if company.company_registry and company.country_code == 'MU':
            return company_details + Markup('<br/> %s') % company.company_registry
        return company_details

    company_details = fields.Html(default=_default_company_details)
