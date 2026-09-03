from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _l10n_fr_pdp_reports_pos_is_transaction_entry(self):
        return self.move_type == 'entry' and self.sudo().pos_session_ids and not self.sudo().reversed_pos_order_id

    def _l10n_fr_pdp_is_sale(self):
        return super()._l10n_fr_pdp_is_sale() or self._l10n_fr_pdp_reports_pos_is_transaction_entry()

    def _l10n_fr_pdp_get_matched_transactions(self):
        if self._l10n_fr_pdp_reports_pos_is_transaction_entry():
            return None
        return super()._l10n_fr_pdp_get_matched_transactions()
