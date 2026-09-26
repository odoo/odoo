from odoo import fields, models


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    l10n_ge_wht_category_ids = fields.Many2many(
        related="partner_id.l10n_ge_wht_category_ids",
        string="Withholding Tax Categories",
    )
