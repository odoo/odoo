from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_ar_withholding_ids = fields.One2many(
        comodel_name="account.move.line",
        inverse_name="move_id",
        string="Withholdings",
        compute="_compute_l10n_ar_withholding_ids",
        readonly=True,
    )

    @api.depends("line_ids")
    def _compute_l10n_ar_withholding_ids(self):
        for move in self:
            move.l10n_ar_withholding_ids = move.line_ids.filtered(
                lambda l: l.tax_line_id.l10n_ar_withholding_payment_type
            )
