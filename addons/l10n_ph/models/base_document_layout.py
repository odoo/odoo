# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class BaseDocumentLayout(models.TransientModel):
    _inherit = 'base.document.layout'

    account_fiscal_country_id = fields.Many2one(related='company_id.account_fiscal_country_id')

    def _l10n_ph_is_vat_registered(self):
        """ The layout preview renders the report templates with the wizard as company. """
        return self.company_id._l10n_ph_is_vat_registered()
