from odoo import api, fields, models


class L10nTrNilveraEinvoiceExtendedAccountTaxCode(models.Model):
    _name = "l10n_tr_nilvera_einvoice_extended.account.tax.code"
    _description = "Turkish Tax Codes (GIB Codes)"

    name = fields.Char(
        string="Reason",
        required=True,
        translate=True,
        help="The official description for this GİB code (e.g., "
        "'Kısmi Tevkifat - Yapım İşleri' or 'Tam İstisna - İhracat').",
    )
    code = fields.Integer(
        string="Reason Code",
        required=True,
        help="The official numeric GİB code (e.g., 601, 301) corresponding to this "
        "reason. This is the value sent in the e-invoice XML.",
    )
    percentage = fields.Float(
        help="Enter the applicable withholding tax rate for this code "
        " as a whole number (e.g., 40 for 40%). \n"
        "This field is used specifically for withholding tax codes and "
        "defines the percentage to be withheld from the total amount."
    )
    code_type = fields.Selection(
        selection=[
            ("withholding", "Withholding"),
            ("exception", "Exception"),
            ("export_exception", "Export Exception"),
            ("export_registration", "Export Registration"),
        ],
        required=True,
        string="Code Type",
        help="Classifies the purpose of the reason. This is used to filter the "
        "correct codes in different parts of Odoo: \n"
        "Withholding: Used for invoices with withholding taxes. \n"
        "Exception: Used for invoices that are tax-exempt. \n"
        "Export Exception: Used for invoices related to product exports that are exempt from certain taxes. \n"
        "Export Registration: Used for invoices that are related to registered export transactions.",
    )


    @api.depends("name", "percentage")
    def _compute_display_name(self):
        for record in self:
            name = record.name
            if record.percentage:
                name = f"{record.percentage * 100}% {name}"
            record.display_name = name
