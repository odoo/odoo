from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    group_purchase_alternatives = fields.Boolean(
        string="Purchase Alternatives",
        implied_group="purchase_requisition.group_purchase_alternatives",
    )
