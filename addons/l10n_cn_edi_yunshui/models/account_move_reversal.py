# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models

from .l10n_cn_edi_document import RED_FORM_REASONS


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    l10n_cn_edi_red_form_reason = fields.Selection(
        selection=RED_FORM_REASONS,
        string="Red Form Reason",
        help="Reason code sent with the red form of the credit note.",
    )
    l10n_cn_edi_use_red_form_reason = fields.Boolean(compute='_compute_l10n_cn_edi_use_red_form_reason')

    @api.depends('move_ids', 'move_type', 'company_id')
    def _compute_l10n_cn_edi_use_red_form_reason(self):
        for wizard in self:
            wizard.l10n_cn_edi_use_red_form_reason = (
                wizard.company_id.account_fiscal_country_id.code == 'CN'
                and wizard.move_type in ('out_invoice', 'in_invoice')
                and bool(wizard.move_ids)
                and wizard.company_id._l10n_cn_edi_is_ready()
            )

    @api.onchange('l10n_cn_edi_red_form_reason')
    def _onchange_l10n_cn_edi_red_form_reason(self):
        for wizard in self:
            if wizard.l10n_cn_edi_use_red_form_reason and wizard.l10n_cn_edi_red_form_reason:
                label = dict(RED_FORM_REASONS).get(wizard.l10n_cn_edi_red_form_reason)
                wizard.reason = (label and label[3:]) or False

    def _prepare_default_reversal(self, move):
        # EXTENDS 'account'
        values = super()._prepare_default_reversal(move)
        if self.l10n_cn_edi_red_form_reason:
            values['l10n_cn_edi_red_form_reason'] = self.l10n_cn_edi_red_form_reason
        return values
