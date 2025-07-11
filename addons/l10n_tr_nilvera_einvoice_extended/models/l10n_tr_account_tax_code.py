from odoo import api, models, fields


class L10nTrAccountTaxCode(models.Model):
    _name = "l10n_tr.account.tax.code"
    _description = "Turkish Tax Codes"

    name = fields.Char(string="Reason", required=True, translate=True)
    code = fields.Integer(string="Reason Code", required=True)
    percentage = fields.Float()
    code_type = fields.Selection(
        [
            ("withholding", "Withholding Code"),
            ("exception", "Exception Code"),
            ("export_exception", "Export Exception Code"),
            ("export_registration", "Export Registration Code"),
        ],
        required=True,
        string="Code Type",
    )

    @api.depends("name", "percentage")
    def _compute_display_name(self):
        for record in self:
            name = record.name
            if record.percentage:
                name = f"{record.percentage * 100}% {name}"
            record.display_name = name
