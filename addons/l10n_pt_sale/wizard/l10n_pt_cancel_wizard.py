from odoo import models


class L10nPtCancelWizard(models.TransientModel):
    _inherit = "l10n_pt.cancel"

    def button_cancel(self):
        self.ensure_one()
        if self.env.context.get('model') == 'sale.order':
            records = self.env['sale.order'].browse(self.env.context.get('order_ids'))
            # Reset print version, since cancelled documents also have an Original and Reprint version
            records.l10n_pt_print_version = None
            return records.write({'l10n_pt_cancel_reason': self.l10n_pt_cancel_reason.strip()})
        return super().button_cancel()
