from odoo import fields, models


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    intermediary_bank_bic = fields.Char(
        "Intermediary SWIFT",
        help="An intermediary bank facilitates international wire transfers between your bank and the beneficiary's bank when they don't have a direct relationship.",
    )
