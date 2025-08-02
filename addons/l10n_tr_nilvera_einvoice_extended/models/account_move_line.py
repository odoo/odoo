from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    l10n_tr_gibp_number = fields.Char(
        string="GIBP Number",
        compute="_compute_l10n_tr_gibp_number",
        store=True,
        readonly=False,
    )

    @api.depends("product_id.l10n_tr_gibp_number")
    def _compute_l10n_tr_gibp_number(self):
        for record in self:
            record.l10n_tr_gibp_number = record.product_id.l10n_tr_gibp_number
