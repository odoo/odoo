from odoo import fields, models


class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    country_code = fields.Char(
        related="company_id.account_config_id.account_fiscal_country_id.code"
    )
