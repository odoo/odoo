from odoo import fields, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_fr_pdp_tt81_category = fields.Selection(
        selection=[
            ('TLB1', "TLB1 - Taxable goods"),
            ('TPS1', "TPS1 - Taxable services"),
            ('TNT1', "TNT1 - Non-taxable operations"),
            ('TMA1', "TMA1 - Margin scheme"),
        ],
        string="PDP TT-81 Category",
        help="Overrides the TT-81 category code for B2C aggregated transactions (Flux 10.3).",
    )
    l10n_fr_pdp_vatex_code = fields.Char(
        string="PDP VATEX Code",
        help="VAT exemption reason code (BT-121) used for Flux 10.1 mapping.",
    )
    l10n_fr_pdp_vatex_reason = fields.Char(
        string="PDP VATEX Reason",
        help="VAT exemption reason text (BT-120) used for Flux 10.1 mapping.",
    )
