from odoo import api, models


class AccountPaymentRegisterWithholdingLine(models.TransientModel):
    _inherit = "account.payment.register.withholding.line"

    @api.depends("payment_register_id.partner_id.l10n_ge_wht_category_ids")
    def _compute_l10n_ge_tax_id_domain(self):
        """Adds a dependency to the partner's withholding tax categories."""
        super()._compute_l10n_ge_tax_id_domain()
