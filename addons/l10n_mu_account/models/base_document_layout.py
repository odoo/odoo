from markupsafe import Markup

from odoo import api, fields, models


class BaseDocumentLayout(models.TransientModel):
    _inherit = 'base.document.layout'

    @api.model
    def _default_company_details(self):
        company_details = super()._default_company_details()
        company = self.env.company
        if company.country_code == 'MU':
            brn = company.partner_id._get_additional_identifier('MU_BRN')
            if brn:
                return company_details + Markup('<br/> %s') % brn
        return company_details

    company_details = fields.Html(default=_default_company_details)
