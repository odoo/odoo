from odoo import models


class AccountEdiCommon(models.AbstractModel):
    _inherit = 'account.edi.common'

    def _get_default_notes(self, vals):
        notes = super()._get_default_notes(vals)
        if notes:
            notes['PMD'] = vals['invoice']._l10n_fr_pdp_get_late_payment_penalty_note()
        return notes
