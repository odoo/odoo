from datetime import date

from odoo import fields, models
from odoo.tools.misc import formatLang


MIN_SUPPORTED_PERIOD = date(2026, 1, 1)


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
        applicable_moves = self.filtered(lambda move: move._l10n_fr_pdp_is_late_payment_penalties_applicable())
        moves_by_company_and_period = {}
        for move in applicable_moves:
            period_start = move.company_id._l10n_fr_pdp_get_semester_start(move.invoice_date)
            if (
                period_start < MIN_SUPPORTED_PERIOD
                and move.company_id.l10n_fr_pdp_late_payment_penalties_automatic
            ):
                continue
            key = (move.company_id, period_start)
            moves_by_company_and_period.setdefault(key, self.env['account.move'])
            moves_by_company_and_period[key] |= move

        periods_to_fetch = sorted({
            period_start
            for company, period_start in moves_by_company_and_period
            if (
                company.l10n_fr_pdp_late_payment_penalties_automatic
                and company.l10n_fr_pdp_late_payment_penalties_period != period_start
                and company._get_peppol_edi_mode() != 'demo'
            )
        })
        rates_by_period = (
            applicable_moves.company_id[:1]._l10n_fr_pdp_fetch_late_payment_penalties_rates(periods_to_fetch)
            if periods_to_fetch
            else {}
        )

        for (company, period_start), moves in moves_by_company_and_period.items():
            rate = company._l10n_fr_pdp_get_late_payment_penalties_rate(period_start, rates_by_period)
            if rate is False:
                rate = company.l10n_fr_pdp_late_payment_penalties_rate
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
