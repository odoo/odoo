from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    l10n_tr_ctsp_number = fields.Char(
        string="CTSP Number",
        compute="_compute_l10n_tr_ctsp_number",
        store=True,
        readonly=False,
    )

    @api.depends("product_id.l10n_tr_ctsp_number")
    def _compute_l10n_tr_ctsp_number(self):
        for record in self:
            record.l10n_tr_ctsp_number = record.product_id.l10n_tr_ctsp_number

    @api.constrains("l10n_tr_ctsp_number")
    def _check_l10n_tr_ctsp_number(self):
        for record in self:
            if record.l10n_tr_ctsp_number and len(record.l10n_tr_ctsp_number) > 12:
                raise ValidationError(_("CTSP Number must be 12 digits or fewer."))
