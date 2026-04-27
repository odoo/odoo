# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_co_dian_mandate_principal = fields.Many2one(comodel_name='res.partner', string="Mandate Principal")

    # -------------------------------------------------------------------------
    # Compute
    # -------------------------------------------------------------------------

    @api.depends('line_ids')
    def _compute_operation_type(self):
        super()._compute_operation_type()
        for move in self:
            if (
                move.move_type in ('in_invoice', 'out_invoice')
                and not move.journal_id.l10n_co_edi_debit_note
                and move.line_ids.product_id.filtered('l10n_co_dian_mandate_contract')
            ):
                move.l10n_co_edi_operation_type = '11'
