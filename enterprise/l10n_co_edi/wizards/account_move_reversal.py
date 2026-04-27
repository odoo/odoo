# -*- coding: utf-8 -*-

from odoo import models, fields

from ..models.account_invoice import DESCRIPTION_CREDIT_CODE


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    l10n_co_edi_description_code_credit = fields.Selection(DESCRIPTION_CREDIT_CODE,
                                                           string="Concepto", help="Colombian code for Credit Notes")

    def _prepare_default_reversal(self, move):
        """Set the Credit Note Concept (Concepto Nota de Credit) selected in the wizard."""
        res = super()._prepare_default_reversal(move)
        if self.country_code == 'CO':
            res['l10n_co_edi_description_code_credit'] = self.l10n_co_edi_description_code_credit
        return res
