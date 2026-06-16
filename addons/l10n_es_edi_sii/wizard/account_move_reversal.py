from odoo import api, fields, models
from odoo.addons.l10n_es_edi_sii.models.account_move import SII_REFUND_REASONS
from odoo.exceptions import UserError


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    l10n_es_sii_refund_reason = fields.Selection(
        selection=SII_REFUND_REASONS,
        string="Invoice Refund Reason",
        help="BOE-A-1992-28740. Ley 37/1992, de 28 de diciembre, del Impuesto sobre el "
        "Valor Añadido. Artículo 80. Modificación de la base imponible.",
        compute="_compute_l10n_es_sii_refund_reason"
    )

    l10n_es_edi_is_required = fields.Boolean(
        compute="_compute_l10n_es_edi_is_required",
        string="Is SII required for this reversal",
    )

    def _prepare_default_reversal(self, move):
        values = super()._prepare_default_reversal(move)
        if move.l10n_es_edi_is_required:
            values.update({
                'l10n_es_sii_refund_reason': self.l10n_es_sii_refund_reason
            })
        if self.l10n_es_sii_refund_reason == 'R5':
            values['l10n_es_is_simplified'] = True

        return values

    @api.depends('move_ids')
    def _compute_l10n_es_edi_is_required(self):
        for wizard in self:
            moves_edi_is_required = {m.l10n_es_edi_is_required for m in wizard.move_ids}
            if len(moves_edi_is_required) > 1:
                raise UserError(self.env._("Reversals mixing invoices with and without SII are not allowed."))
            wizard.l10n_es_edi_is_required = moves_edi_is_required.pop()

    @api.depends('move_ids.l10n_es_is_simplified')
    def _compute_l10n_es_sii_refund_reason(self):
        for wizard in self:
            if not wizard.l10n_es_edi_is_required:
                wizard.l10n_es_sii_refund_reason = False
            elif any(m.l10n_es_is_simplified for m in wizard.move_ids):
                wizard.l10n_es_sii_refund_reason = 'R5'
            else:
                wizard.l10n_es_sii_refund_reason = 'R4'
