from odoo import fields, models


class ReturnPicking(models.TransientModel):
    _inherit = "stock.return.picking.line"

    move_external_id = fields.Char(string="External ID for stock move")
