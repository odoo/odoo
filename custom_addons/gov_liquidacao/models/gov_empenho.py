from odoo import fields, models


class GovEmpenho(models.Model):
    _inherit = "gov.empenho"

    liquidacao_ids = fields.One2many(
        "gov.liquidacao",
        "empenho_id",
        string="Liquidações vinculadas",
    )
