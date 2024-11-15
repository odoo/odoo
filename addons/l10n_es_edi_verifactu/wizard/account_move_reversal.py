from odoo import api, fields, models


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    l10n_es_edi_verifactu_required = fields.Boolean(
        string="Veri*Factu Required",
        compute="_compute_l10n_es_edi_verifactu_required", store=True,
    )

    l10n_es_edi_verifactu_refund_reason = fields.Selection(
        selection=[
            ('R1', "R1: Art 80.1 and 80.2 and error of law"),
            ('R2', "R2: Art. 80.3"),
            ('R3', "R3: Art. 80.4"),
            ('R4', "R4: Rest"),
            ('R5', "R5: Corrective invoices concerning simplified invoices"),
        ],
        string="Veri*Factu Refund Reason",
        compute="_compute_l10n_es_edi_verifactu_refund_reason", store=True, readonly=False,
    )

    @api.depends('move_ids.l10n_es_edi_verifactu_required')
    def _compute_l10n_es_edi_verifactu_required(self):
        for wizard in self:
            wizard.l10n_es_edi_verifactu_required = any(wizard.move_ids.mapped('l10n_es_edi_verifactu_required'))

    @api.depends('move_ids.l10n_es_edi_verifactu_required')
    def _compute_l10n_es_edi_verifactu_refund_reason(self):
        for wizard in self:
            refund_reason = False
            if wizard.l10n_es_edi_verifactu_required:
                refund_reason = 'R4'
            wizard.l10n_es_edi_verifactu_refund_reason = refund_reason

    def _prepare_default_reversal(self, move):
        # EXTEND 'account'
        values = super()._prepare_default_reversal(move)
        if refund_reason := self.l10n_es_edi_verifactu_refund_reason:
            values['l10n_es_edi_verifactu_refund_reason'] = refund_reason
        return values

    def _modify_default_reverse_values(self, origin_move):
        # EXTEND 'account'
        values = super()._modify_default_reverse_values(origin_move)
        values['l10n_es_edi_verifactu_substituted_entry_id'] = origin_move.id
        if refund_reason := self.l10n_es_edi_verifactu_refund_reason:
            values['l10n_es_edi_verifactu_refund_reason'] = refund_reason
        return values
