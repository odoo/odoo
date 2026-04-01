from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    l10n_tw_edi_ecpay_item_sequence = fields.Integer(string="Item Sequence", readonly=True)
