from odoo import api, fields, models


class L10nTrNilveraEinvoiceExtendedAccountTaxCode(models.Model):
    _name = "l10n_tr_nilvera_einvoice_extended.account.tax.code"
    _description = "Turkish Tax Codes (GIB Codes)"

    name = fields.Char(string="Reason", required=True, translate=True)
    code = fields.Integer(string="Reason Code", required=True)
    percentage = fields.Float()
    code_type = fields.Selection(
        selection=[
            ("withholding", "Withholding"),
            ("exception", "Exception"),
            ("export_exception", "Export Exception"),
            ("export_registration", "Export Registration"),
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
