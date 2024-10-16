from odoo import models
from odoo.addons import l10n_in_withholding


class L10n_InWithholdWizard(l10n_in_withholding.L10n_InWithholdWizard):

    def _prepare_withhold_header(self):
        res = super()._prepare_withhold_header()
        if self.related_payment_id:
            res['l10n_in_withholding_ref_payment_id'] = self.related_payment_id.id
        return res
