from markupsafe import Markup

from odoo import api, models


class BaseDocumentLayout(models.TransientModel):
    _inherit = 'base.document.layout'

    @api.model
    def _default_company_details(self):
        if self.env.company.country_code != 'SA':
            return super()._default_company_details()

        additional_company_details = ""

        if self.env.company.vat:
            additional_company_details += Markup('VAT Number: %s <br/>') % self.env.company.vat
        if (code := self.env.company.l10n_sa_edi_additional_identification_scheme) and self.env.company.l10n_sa_edi_additional_identification_number:
            code_value = dict(self._fields['l10n_sa_edi_additional_identification_scheme']._description_selection(self.env))[code]
            additional_company_details += f"{code_value}: {self.env.company.l10n_sa_edi_additional_identification_number}"

        return super()._default_company_details() + Markup('<br/><br/>%s') % additional_company_details
