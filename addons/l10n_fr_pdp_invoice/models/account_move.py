from odoo import fields, models
from odoo.tools.misc import formatLang


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_fr_pdp_late_payment_penalties_rate = fields.Float(
        string="Late Payment Penalties Rate",
        default=10.0,
        digits=(16, 2),
        copy=False,
        readonly=True,
        help="Late payment penalties rate that applied when the invoice was posted.",
    )

    def _l10n_fr_pdp_is_late_payment_penalties_applicable(self):
        self.ensure_one()
        return (
            self.state == 'posted'
            and self.is_sale_document(include_receipts=False)
            and self.company_id.l10n_fr_pdp_late_payment_penalties_applicable
        )

    def _l10n_fr_pdp_set_late_payment_penalties_rate(self):
        moves_by_company_and_period = {}
        periods_by_company = {}
        for move in self:
            if not move._l10n_fr_pdp_is_late_payment_penalties_applicable():
                continue
            period_start = move.company_id._l10n_fr_pdp_get_semester_start(move.invoice_date)
            key = (move.company_id, period_start)
            moves_by_company_and_period.setdefault(key, self.env['account.move'])
            moves_by_company_and_period[key] |= move
            periods_by_company.setdefault(move.company_id, set()).add(period_start)

        rates_by_company = {
            company: company._l10n_fr_pdp_get_late_payment_penalties_rates(period_starts)
            for company, period_starts in periods_by_company.items()
        }

        for (company, period_start), moves in moves_by_company_and_period.items():
            rate = rates_by_company[company].get(period_start)
            if rate is None:
                rate = company.l10n_fr_pdp_manual_late_payment_penalties_rate
                moves.l10n_fr_pdp_late_payment_penalties_rate = rate
                formatted_rate = formatLang(self.env, rate, digits=0 if rate.is_integer() else 2)
                warning = self.env._(
                    "The late payment penalty rate could not be updated. "
                    "The current rate of %(rate)s%% was used. If necessary, reset "
                    "the invoice to draft and adjust the rate manually in the Accounting "
                    "settings, or contact Odoo Support.",
                    rate=formatted_rate,
                )
                for move in moves:
                    move._message_log(body=warning)
            else:
                moves.l10n_fr_pdp_late_payment_penalties_rate = rate

    def _post(self, soft=True):
        moves = super()._post(soft)
        moves._l10n_fr_pdp_set_late_payment_penalties_rate()
        return moves

    def _l10n_fr_pdp_get_late_payment_penalty_note(self):
        self.ensure_one()
        rate = self.l10n_fr_pdp_late_payment_penalties_rate
        formatted_rate = formatLang(self.env, rate, digits=0 if rate.is_integer() else 2)
        return self.env._(
            "Late payment penalties at an annual rate of %(rate)s%% are applied "
            "if the payment is made after the due date.",
            rate=formatted_rate,
        )

    def _l10n_fr_pdp_get_default_notes(self):
        notes = super()._l10n_fr_pdp_get_default_notes()
        if notes:
            notes['PMD'] = self._l10n_fr_pdp_get_late_payment_penalty_note()
        return notes
