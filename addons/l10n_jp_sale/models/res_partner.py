# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_jp_closing_day_ids = fields.Many2many(
        comodel_name='l10n_jp.closing.day',
        string="Closing Dates",
        help="Days of the month on which the orders of this customer are closed, to be billed on one summary invoice.",
    )
    l10n_jp_pay_at_next_closing = fields.Boolean(
        string="Pay at Next Closing Date",
        help="Summary invoices are due at the closing date that follows theirs, whatever the payment terms.",
    )

    def _l10n_jp_get_closing_dates(self, date):
        """Return the closing dates of the previous, current and next month of the given date."""
        self.ensure_one()
        return sorted({
            # A day past the end of the month falls on its last day.
            date + relativedelta(months=months, day=closing_day.day)
            for months in (-1, 0, 1)
            for closing_day in self.l10n_jp_closing_day_ids
        })
