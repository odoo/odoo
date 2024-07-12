from odoo import models
from odoo.exceptions import UserError


class ResCompany(models.Model):
    _inherit = "res.company"

    def _l10n_pt_stock_action_check_hash_integrity(self):
        return self.env.ref('l10n_pt_stock.action_l10n_pt_stock_report_hash_integrity').report_action(self.id)

    def _l10n_pt_stock_check_hash_integrity(self):
        if self.account_fiscal_country_id.code != 'PT':
            raise UserError(self.env._('This feature is only available for Portuguese companies.'))
        return self.env['stock.picking']._l10n_pt_check_hash_integrity(self)
