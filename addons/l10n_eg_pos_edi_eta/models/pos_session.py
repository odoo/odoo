from odoo import models, _
from odoo.exceptions import UserError


class POSSession(models.Model):
    _inherit = 'pos.session'

    def _validate_session(self, balancing_account=False, amount_to_balance=0, bank_payment_method_diffs=None):
        """
            Override to add checks on the ETA Submissions status when trying to close a session
        """
        for order_id in self.order_ids:
            if not order_id.country_code == 'EG':
                continue
            if order_id.l10n_eg_pos_eta_state == 'pending':
                raise UserError(_("Cannot close a session if any of the receipts still need to be sent to the ETA"))
            elif order_id.l10n_eg_pos_eta_state == 'sent' and order_id.l10n_eg_pos_eta_submission_state != 'valid':
                order_id.l10n_eg_pos_eta_check_submissions()
                if order_id.l10n_eg_pos_eta_submission_state == 'invalid':
                    order_id.action_pos_order_invoice()
        return super(POSSession, self)._validate_session(balancing_account, amount_to_balance,
                                                         bank_payment_method_diffs)
