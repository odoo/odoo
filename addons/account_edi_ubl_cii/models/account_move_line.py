from odoo import models, fields


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    seller_item_identification = fields.Char(nullable=True)
    buyer_item_identification = fields.Char(nullable=True)
    standard_item_identification = fields.Char(nullable=True)
