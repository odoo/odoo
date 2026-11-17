from odoo import models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _compute_tax_ids(self):
        super()._compute_tax_ids()
        for line in self:
            if product := line.product_id:
                line.tax_ids += (product.l10n_fr_rate_id + product.l10n_fr_regional_rate_id)
