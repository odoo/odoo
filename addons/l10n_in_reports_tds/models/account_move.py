# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_in_move_id = fields.Many2one('account.move')
    l10n_in_is_tds = fields.Boolean(string="Is TDS Entry", default=False, readonly=False)

    def _compute_payments_widget_reconciled_info(self):
        super()._compute_payments_widget_reconciled_info()
        for move in self:
            if move.invoice_payments_widget:
                for reconciled_val in move.invoice_payments_widget.get('content', []):
                    reconciled_move_id = reconciled_val.get('move_id')
                    reconciled_move = reconciled_move_id and self.browse(reconciled_move_id) or False
                    if reconciled_move and reconciled_move.l10n_in_is_tds:
                        reconciled_val['l10n_in_is_tds'] = True
