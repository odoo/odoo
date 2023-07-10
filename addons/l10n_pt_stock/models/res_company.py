from odoo import models


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _l10n_pt_stock_action_check_blockchain_integrity(self):
        return self.env.ref('l10n_pt_stock.l10n_pt_stock_action_report_stock_blockchain_integrity').report_action(self.id)
