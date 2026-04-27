from odoo import models


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    def _prepare_default_reversal(self, move):
        """When reversing an invoice, set the new credit note doc type automatically to NCRE"""
        res = super()._prepare_default_reversal(move)
        res['l10n_gt_edi_doc_type'] = False
        if self.country_code == 'GT' and self.company_id.l10n_gt_edi_vat_affiliation == 'GEN':
            res['l10n_gt_edi_doc_type'] = 'NCRE'
        return res
