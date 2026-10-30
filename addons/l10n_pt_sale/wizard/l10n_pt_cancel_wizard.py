from odoo import models


class L10nPtCancelWizard(models.TransientModel):
    _inherit = "l10n_pt.cancel"

    def button_cancel(self):
        self.ensure_one()
        if self.env.context.get('model') == 'sale.order':
            records = self.env['sale.order'].browse(self.env.context.get('order_ids'))
            records.l10n_pt_cancel_reason = self.l10n_pt_cancel_reason.strip()
            return records.action_cancel()
        return super().button_cancel()
