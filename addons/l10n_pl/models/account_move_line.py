from odoo import models, fields


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _compute_currency_rate(self):
        l10n_pl_lines = self.filtered(
            lambda line: (
                line.move_id.country_code == 'PL'
                and line.move_id.reversed_entry_id
                and line.currency_id
            )
        )
        for line in l10n_pl_lines:
            line.currency_rate = self.env['res.currency']._get_conversion_rate(
                    from_currency=line.company_currency_id,
                    to_currency=line.currency_id,
                    company=line.company_id,
                    date=line.move_id.reversed_entry_id.delivery_date or line.move_id.reversed_entry_id.date or fields.Date.context_today(line),
                )

        super(AccountMoveLine, (self - l10n_pl_lines))._compute_currency_rate()
