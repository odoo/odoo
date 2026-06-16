# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime

from dateutil.relativedelta import relativedelta

from odoo import api, models


class AccountPaymentRegisterWithholdingLine(models.TransientModel):
    _inherit = 'account.payment.register.withholding.line'

    @api.depends('payment_register_id.amount', 'tax_id')
    def _compute_base_amount(self):
        # EXTENDS 'l10n_account_withholding_tax' - AR taxes derive their base from the wizard amount:
        # `iibb_total` uses the full wizard amount, others use the untaxed portion via untaxed/total ratio.
        ar_lines = self.filtered(lambda l: l.tax_id.is_withholding_tax_on_payment and l.company_id.account_fiscal_country_id.code == 'AR')
        super(AccountPaymentRegisterWithholdingLine, self - ar_lines)._compute_base_amount()
        for line in ar_lines:
            wizard = line.payment_register_id
            if line.tax_id.l10n_ar_tax_type == 'iibb_total':
                line.base_amount = wizard.amount
            else:
                untaxed = sum(wizard.line_ids.mapped('move_id.amount_untaxed'))
                total = sum(wizard.line_ids.mapped('move_id.amount_total'))
                line.base_amount = wizard.amount * (untaxed / total) if total else wizard.amount

    @api.depends('base_amount', 'tax_id')
    def _compute_amount(self):
        # EXTENDS 'l10n_account_withholding_tax' - AR taxes use bespoke arithmetic
        # (earnings accumulation, scale brackets, non-taxable amount, minimum threshold).
        ar_lines = self.filtered(lambda l: l.tax_id.is_withholding_tax_on_payment and l.company_id.account_fiscal_country_id.code == 'AR')
        super(AccountPaymentRegisterWithholdingLine, self - ar_lines)._compute_amount()
        for line in ar_lines:
            if not line.tax_id:
                line.amount = 0.0
            else:
                line.amount = line._l10n_ar_compute_withholding_amount()

    def _l10n_ar_compute_withholding_amount(self):
        """ Compute the AR withholding amount in the line's `comodel_currency_id` (the payment currency).

        AR fiscal rules (non-taxable amount, minimum threshold, earnings accumulation, scale brackets)
        are expressed in ARS. We convert `base_amount` to ARS, run the rule, then convert back.
        """
        self.ensure_one()
        company_currency = self.company_id.currency_id
        line_currency = self.comodel_currency_id
        wizard = self.payment_register_id

        base_ars = line_currency._convert(
            self.base_amount, company_currency, self.company_id, wizard.payment_date,
        )
        if self.tax_id.l10n_ar_tax_type in ('earnings', 'earnings_scale'):
            tax_amount_ars = self._l10n_ar_compute_earnings_amount(base_ars)
        else:
            net_amount = max(0.0, base_ars - self.tax_id.l10n_ar_non_taxable_amount)
            tax_amount_ars = company_currency.round(net_amount * abs(self.tax_id.amount) / 100.0)
            if self.tax_id.l10n_ar_minimum_threshold > tax_amount_ars:
                tax_amount_ars = 0.0
        return company_currency._convert(
            tax_amount_ars, line_currency, self.company_id, wizard.payment_date,
        )

    def _l10n_ar_compute_earnings_amount(self, base_ars):
        """Apply earnings / earnings_scale rules entirely in ARS, returning the tax amount in ARS."""
        self.ensure_one()
        company_currency = self.company_id.currency_id
        to_date = self.payment_register_id.payment_date or datetime.date.today()
        from_date = to_date + relativedelta(day=1)
        partner = self.payment_register_id.partner_id.commercial_partner_id

        same_period_withholdings = 0.0
        same_period_base = 0.0
        domain_same_period_withholdings = [
            ('company_id', 'child_of', self.tax_id.company_id.id),
            ('parent_state', '=', 'posted'),
            ('tax_line_id.l10n_ar_code', '=', self.tax_id.l10n_ar_code),
            ('tax_line_id.l10n_ar_tax_type', 'in', ('earnings', 'earnings_scale')),
            ('partner_id', '=', partner.id),
            ('date', '<=', to_date),
            ('date', '>=', from_date),
        ]
        if same_period_partner_withholdings := self.env['account.move.line'].sudo()._read_group(
            domain_same_period_withholdings, ['partner_id'], ['balance:sum'],
        ):
            same_period_withholdings = abs(same_period_partner_withholdings[0][1])
        domain_same_period_base = [
            ('company_id', 'child_of', self.tax_id.company_id.id),
            ('parent_state', '=', 'posted'),
            ('tax_ids.l10n_ar_code', '=', self.tax_id.l10n_ar_code),
            ('tax_ids.l10n_ar_tax_type', 'in', ('earnings', 'earnings_scale')),
            ('partner_id', '=', partner.id),
            ('date', '<=', to_date),
            ('date', '>=', from_date),
        ]
        if same_period_partner_base := self.env['account.move.line'].sudo()._read_group(
            domain_same_period_base, ['partner_id'], ['balance:sum'],
        ):
            same_period_base = abs(same_period_partner_base[0][1])

        net_amount = max(0.0, base_ars + same_period_base - self.tax_id.l10n_ar_non_taxable_amount)

        if self.tax_id.l10n_ar_tax_type == 'earnings_scale':
            scale = self.env['l10n_ar.earnings.scale.line'].search([
                ('scale_id', '=', self.tax_id.l10n_ar_scale_id.id),
                ('excess_amount', '<=', net_amount),
                ('to_amount', '>', net_amount),
            ], limit=1)
            tax_amount = ((net_amount - scale.excess_amount) * scale.percentage / 100.0) + scale.fixed_amount if scale else 0.0
        else:
            tax_amount = company_currency.round(net_amount * abs(self.tax_id.amount) / 100.0)

        tax_amount -= same_period_withholdings

        if self.tax_id.l10n_ar_minimum_threshold > tax_amount:
            tax_amount = 0.0
        return tax_amount
