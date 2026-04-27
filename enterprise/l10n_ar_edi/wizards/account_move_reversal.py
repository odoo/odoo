# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class AccountMoveReversal(models.TransientModel):
    _inherit = "account.move.reversal"

    l10n_ar_afip_fce_is_cancellation = fields.Boolean(string='FCE: Is Cancellation?',
        help='Argentina: When informing a MiPyMEs (FCE) debit/credit notes in AFIP it is required to send information about whether the'
        ' original document has been explicitly rejected by the buyer. More information here'
        ' http://www.afip.gob.ar/facturadecreditoelectronica/preguntasFrecuentes/emisor-factura.asp')

    def _prepare_default_reversal(self, move):
        res = super()._prepare_default_reversal(move)
        if move.company_id.account_fiscal_country_id.code == "AR":
            res.update({
                'l10n_ar_afip_fce_is_cancellation': self.l10n_ar_afip_fce_is_cancellation,
            })
        return res
