from odoo import api, models


class AccountPaymentWithholdingLine(models.Model):
    _inherit = "account.payment.withholding.line"

    @api.depends(
        "company_id",
        "country_code",
        "comodel_payment_type",
        "payment_id.partner_id.l10n_ge_wht_category_ids",
    )
    def _compute_l10n_ge_tax_id_custom_domain(self):
        super()._compute_l10n_ge_tax_id_custom_domain()
