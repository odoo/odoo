from odoo import models, fields
from odoo.fields import Domain
from odoo.tools.date_utils import start_of, end_of

from odoo.addons.l10n_ar_withholding.models.account_tax import EARNINGS_TAX_TYPES


class ResPartner(models.Model):
    _inherit = "res.partner"
    # FIXME note we created this 'l10n_ar.partner.tax' system for simplification, but it's not really correct.
    # I think the accumulation should be per product category ("conceptos") per partner, not just per partner.
    # If an invoice has a line with freight (78) and fees(116), that's two regimes.
    # The tax from the freight regime should only apply to the invoice lines of that product category, and vice-versa.
    # TLDR; the current implementation only supports one regime at a time.

    l10n_ar_partner_tax_ids = fields.One2many(
        'l10n_ar.partner.tax',
        'partner_id',
        'Argentinean Withholding Taxes',
    )

    def _l10n_ar_get_withholding_taxes_from_regime(self, company, type_tax_use, date=False):
        """ Return the withholding taxes owed for this partner, that is the ones of the regimes it
            is registered in (see l10n_ar.partner.tax), in force at the given date if one is given. """
        self.ensure_one()
        PartnerTax = self.env['l10n_ar.partner.tax']
        domain = Domain([
            *PartnerTax._check_company_domain(company),
            ('partner_id', '=', self.commercial_partner_id.id),
            ('tax_id.is_withholding_tax', '=', True),
            ('tax_id.type_tax_use', '=', type_tax_use),
            ('tax_id.active', '=', True),
        ])
        if date:
            domain &= (
                (Domain('from_date', '<=', date) | Domain('from_date', '=', False))
                & (Domain('to_date', '>=', date) | Domain('to_date', '=', False))
            )
        return PartnerTax.search(domain).tax_id

    def _l10n_ar_get_period_accumulation(self, tax, date, exclude_payment=None):
        """ Earnings withholdings are computed on everything paid to the partner since the beginning
            of the month. Return what already accumulated this month for the regime of the tax.

            :param tax: the withholding tax whose regime is accumulated.
            :param date: the date of the payment being computed.
            :param exclude_payment: a payment to leave out, typically the one being computed.
            :return: a dict with the 'base' already levied on and the 'withheld' already taken, as well
            as the currency of these amounts.
        """
        self.ensure_one()
        assert tax.l10n_ar_withholding_tax_type in EARNINGS_TAX_TYPES, "Doesn't make sense to compute accumulation for other regimes"
        domain = Domain([
            ('company_id', 'child_of', tax.company_id.id),
            ('parent_state', '=', 'posted'),
            ('date', '>=', start_of(date, 'month')),
            ('date', '<=', end_of(date, 'month')),
            ('partner_id', '=', self.commercial_partner_id.id),
        ])
        if exclude_payment:
            # A payment does not accumulate against itself.
            domain &= Domain('payment_id', '!=', exclude_payment.id)

        # Accumulation groups the regimes sharing the same ARCA code.
        # When no code is set, fall back to the tax itself to avoid wrongly grouping all False together.
        regime_domain = Domain([
            ('company_id', 'child_of', tax.company_id.root_id.id),
            ('l10n_ar_withholding_tax_type', 'in', EARNINGS_TAX_TYPES),
        ]) & (Domain('l10n_ar_code', '=', tax.l10n_ar_code) if tax.l10n_ar_code else Domain('id', '=', tax.id))

        withheld = self.env['account.move.line'].sudo()._read_group(
            domain & Domain('tax_line_id', 'any', regime_domain),
            ['partner_id'], ['balance:sum'],
        )
        bases = self.env['account.move.line'].sudo()._read_group(
            domain & Domain('tax_ids', 'any', regime_domain),
            ['partner_id'], ['balance:sum'],
        )

        return {
            'base': bases[0][1] if bases else 0.0,
            'withheld': -withheld[0][1] if withheld else 0.0,
            'currency': tax.company_id.currency_id,  # not strictly necessary but makes it clear that the accumulation is returned in company_currency (ARS)
        }
