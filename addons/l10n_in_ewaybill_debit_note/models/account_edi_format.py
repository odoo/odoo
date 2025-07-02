from odoo import models


class AccountEdiFormat(models.Model):
    _inherit = "account.edi.format"

    def _l10n_in_edi_ewaybill_base_irn_or_direct(self, move):
        if move.debit_origin_id:
            return "direct"
        return super()._l10n_in_edi_ewaybill_base_irn_or_direct(move)
