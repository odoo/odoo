from odoo import models, fields


class AccountPayment(models.Model):
    _inherit = "account.payment"

    l10n_in_withhold_move_ids = fields.One2many(
        'account.move', 'l10n_in_withholding_ref_payment_id',
        string="Indian Payment TDS Entries",
        related=False
    )
    l10n_in_total_withholding_amount = fields.Monetary(compute='_compute_l10n_in_total_withholding_amount', related=False)

    def _compute_l10n_in_total_withholding_amount(self):
        for payment in self:
            payment.l10n_in_total_withholding_amount = sum(payment.l10n_in_withhold_move_ids.filtered(
                lambda m: m.state == 'posted').l10n_in_withholding_line_ids.mapped('l10n_in_withhold_tax_amount'))
