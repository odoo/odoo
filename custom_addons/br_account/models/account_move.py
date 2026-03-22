from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    regime_tributario = fields.Selection(
        related="company_id.regime_tributario",
        readonly=False,
        store=True,
    )
    natureza_operacao = fields.Char()
    finalidade_emissao = fields.Selection(
        [("1", "Normal"), ("2", "Complementar"), ("3", "Ajuste"), ("4", "Devolucao")],
        default="1",
    )

    @api.constrains("state", "date", "journal_id")
    def _check_journal_lock_date_br(self):
        for move in self.filtered(lambda item: item.state == "posted" and item.date and item.journal_id):
            lock_dates = [date for date in [move.company_id.period_lock_date, move.journal_id.lock_date_br] if date]
            if lock_dates and move.date <= max(lock_dates):
                raise ValidationError(
                    _("Nao e permitido contabilizar movimentos em data bloqueada para a empresa ou diario.")
                )

