# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    @api.model
    def _l10n_es_regime_code_labels(self):
        labels = super()._l10n_es_regime_code_labels()
        _ = self.env._
        labels.update({
            '19': _("19 - Activities under the Special Regime for Agriculture, Livestock and Fisheries (REAGYP)"),
            '51': _("51 - Equivalence surcharge"),
            '52': _("52 - Simplified regime"),
            '53': _("53 - Operations by persons/entities not considered businesses or professionals for VAT purposes"),
            '54': _("54 - Operations from a permanent establishment for indirect tax purposes in Canarias, Ceuta or Melilla"),
        })
        return labels

    @api.depends('company_id.l10n_es_tbai_is_enabled')
    def _compute_l10n_es_available_regime_codes(self):
        super()._compute_l10n_es_available_regime_codes()

    @api.depends('company_id.l10n_es_tbai_is_enabled')
    def _compute_l10n_es_regime_code(self):
        super()._compute_l10n_es_regime_code()
