from odoo import fields, models


class Picking(models.Model):
    _inherit = "stock.picking"

    # Added new field #T7157
    return_reason = fields.Html()
