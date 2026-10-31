from odoo import api, models


class AccountPaymentWithholdingLine(models.Model):
    _inherit = "account.payment.withholding.line"

    @api.depends("payment_id.partner_id.l10n_ge_wht_category_ids")
    def _compute_l10n_ge_tax_id_domain(self):
        """Adds a dependency to the partner's withholding tax categories."""
        super()._compute_l10n_ge_tax_id_domain()
