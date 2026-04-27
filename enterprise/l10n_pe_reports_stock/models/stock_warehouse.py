from odoo import fields, models


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    country_code = fields.Char(related='company_id.account_fiscal_country_id.code', readonly=True)
    l10n_pe_anexo_establishment_code = fields.Char(
        string="Annex Establishment Code",
        help="The first four digits are mandatory and correspond to the annex establishment code according to the "
        "Single Taxpayers' Registry. If the warehouse is located in a third-party establishment or it is not possible "
        "to include it as an annex establishment, the first four numbers will be: '9999'. From position 5 to 7, "
        "register a sequential number, if necessary.",
    )
