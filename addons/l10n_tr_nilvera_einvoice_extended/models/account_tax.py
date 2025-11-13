from odoo import fields, models


class AccountTax(models.Model):
    _inherit = "account.tax"

    l10n_tr_tax_withholding_code_id = fields.Many2one(
        comodel_name="l10n_tr_nilvera_einvoice_extended.account.tax.code",
        string="Withholding Reason",
        domain="[('code_type', '=', 'withholding')]",
        help="Select the official GİB withholding reason associated with this tax. \n"
        "This is required when the invoice type is 'Withholding'. \n"
        "The withholding reason determines the specific tax category for withholding "
        "and ensures compliance with Turkish tax regulations.",
    )
