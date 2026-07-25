from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    ai_confidence = fields.Float(
        string='Line AI Confidence',
        digits=(3, 2),
        help="Confidence score for this specific invoice line, set by the AI extraction service.",
    )
