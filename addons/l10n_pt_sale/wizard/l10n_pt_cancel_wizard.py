from odoo import models


class L10nPtCancelWizard(models.TransientModel):
    _inherit = "l10n_pt.cancel"

    def button_cancel(self):
        self.ensure_one()
        if self.env.context.get('active_model') == 'sale.order':
            records = self.env['sale.order'].browse(self.env.context.get('active_ids'))
            # Only an issued PT order is cancelled with a reason; the others are cancelled as they are.
            records._l10n_pt_issued_orders().l10n_pt_cancel_reason = self.l10n_pt_cancel_reason.strip()
            return records.action_cancel()
        return super().button_cancel()
