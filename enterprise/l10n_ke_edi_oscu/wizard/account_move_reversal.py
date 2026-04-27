# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    l10n_ke_reason_code_id = fields.Many2one(
        comodel_name='l10n_ke_edi_oscu.code',
        domain="[('code_type', '=', '32')]",
        string="KRA Reason",
        help="Kenyan code for Credit Notes",
    )

    def _prepare_default_reversal(self, move):
        return {
            'l10n_ke_reason_code_id': self.l10n_ke_reason_code_id.id,
            **super()._prepare_default_reversal(move),
        }
