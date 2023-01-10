from markupsafe import Markup

from odoo import api, models, fields
from odoo.addons.base.models.ir_qweb_fields import nl2br


class BaseDocumentLayout(models.TransientModel):
    _inherit = 'base.document.layout'

    @api.model
    def _default_company_details(self):
        default_company_details = super()._default_company_details()
        if self.env.company.country_code == 'FR':
            # In france, displaying the SIRET number on any invoices is required
            company = self.env.company
            if 'SIRET' not in default_company_details and company.siret:
                default_company_details += Markup(nl2br('\nSIRET: %s')) % company.siret

        return default_company_details

    company_details = fields.Html(default=_default_company_details)
