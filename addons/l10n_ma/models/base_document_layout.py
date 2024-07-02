# Part of Odoo. See LICENSE file for full copyright and licensing details.
from markupsafe import Markup

from odoo import api, models


class BaseDocumentLayout(models.TransientModel):
    _inherit = 'base.document.layout'

    @api.model
    def _default_company_details(self):
        company_details = super()._default_company_details()
        if self.env.company.country_code == 'MA':
            company_details += Markup('<br> ICE: %s', self.env.company.l10n_ma_ice)
        return company_details
