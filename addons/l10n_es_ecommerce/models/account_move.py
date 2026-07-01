from odoo import api, models


class AccountMove(models.Model):

    _inherit = 'account.move'

    @api.depends('partner_id', 'line_ids.balance', 'journal_id')
    def _compute_l10n_es_is_simplified(self):
        super()._compute_l10n_es_is_simplified()
        simplified_journal_ids = {
            jid for jid, ext_id in self.mapped('journal_id').get_external_id().items()
            if ext_id == 'l10n_es_ecommerce.simplified_journal'
        }
        for move in self:
            if move.journal_id.id in simplified_journal_ids:
                move.l10n_es_is_simplified = True
