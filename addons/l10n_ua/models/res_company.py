from markupsafe import Markup

from odoo import api, models, _, fields


class BaseDocumentLayout(models.TransientModel):
    _inherit = 'base.document.layout'

    @api.model
    def _default_company_details(self):
        company_details = super()._default_company_details()
        company = self.env.company
        if company.country_code == 'UA':
            if company.company_registry:
                company_details += Markup('<br/> %s') % _('Registry: %s', company.company_registry)
            if company.bank_ids:
                bank = company.bank_ids[0]
                company_details += Markup('<br/> %s') % _('Bank: %s', bank.display_name)
                if bank.bank_bic:
                    company_details += Markup('<br/> %s') % _('BIC: %s', bank.bank_bic)
        return company_details

    company_details = fields.Html(default=_default_company_details)
