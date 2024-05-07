# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api
from odoo.addons.l10n_es_edi_tbai.models.account_move import TBAI_REFUND_REASONS
from odoo.exceptions import UserError


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    l10n_es_tbai_is_required = fields.Boolean(
        compute="_compute_l10n_es_tbai_is_required", readonly=True,
        string="Is TicketBai required for this reversal",
    )

    l10n_es_tbai_refund_reason = fields.Selection(
        selection=TBAI_REFUND_REASONS,
        string="Invoice Refund Reason Code (TicketBai)",
        help="BOE-A-1992-28740. Ley 37/1992, de 28 de diciembre, del Impuesto sobre el "
        "Valor Añadido. Artículo 80. Modificación de la base imponible.",
    )

    @api.depends('move_ids')
    def _compute_l10n_es_tbai_is_required(self):
        for wizard in self:
            moves_tbai_required = set(m.l10n_es_tbai_is_required for m in wizard.move_ids)
            if len(moves_tbai_required) > 1:
                raise UserError("Reversals mixing invoices with and without TicketBAI are not allowed.")
            wizard.l10n_es_tbai_is_required = moves_tbai_required.pop()

    def _prepare_default_reversal(self, move):
        # OVERRIDE
        values = super()._prepare_default_reversal(move)
        if move.l10n_es_tbai_is_required:
            values.update({
                'l10n_es_tbai_refund_reason': self.l10n_es_tbai_refund_reason,
            })
        return values
