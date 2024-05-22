from odoo import api, models, fields


class AccountMove(models.Model):
    _inherit = 'account.move'

    amount_total_words = fields.Char("Amount total in words", compute="_compute_amount_total_words")

    @api.depends('amount_total', 'currency_id')
    def _compute_amount_total_words(self):
        for record in self:
            record.amount_total_words = record.currency_id.amount_to_text(record.amount_total)
