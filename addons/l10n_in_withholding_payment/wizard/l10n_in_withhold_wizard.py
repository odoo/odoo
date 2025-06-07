from odoo import models


class L10nInWithholdWizard(models.TransientModel):
    _inherit = 'l10n_in.withhold.wizard'

    def _prepare_withhold_header(self):
        res = super()._prepare_withhold_header()
        if self.related_payment_id:
            res['l10n_in_withholding_ref_payment_id'] = self.related_payment_id.id
        return res
