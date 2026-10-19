from odoo import models

from odoo.addons.l10n_ar_withholding.models.account_tax import EARNINGS_TAX_TYPES


class AccountWithholdingLine(models.AbstractModel):
    _inherit = 'account.withholding.line'

    def _compute_amount(self):
        """ EXTENDS 'l10n_account_withholding_tax' - AR withholding purchase taxes needs special computation. """
        ar_lines = self.filtered(lambda l: l.country_code == 'AR' and l.tax_id.type_tax_use == 'purchase')
        ars_currency = self.env.ref('base.ARS')
        for line in ar_lines:
            # ARCA scales amounts are in ARS, explicitly convert amount to it to avoid summing apples and pears
            line_currency, date = line.comodel_currency_id, line.comodel_date
            net_amount_in_ars = line_currency._convert(
                from_amount=line.base_amount,
                to_currency=ars_currency,
                company=line.company_id,
                date=date,
            )
            same_period_withheld = 0.0
            if line.tax_id.l10n_ar_withholding_tax_type in EARNINGS_TAX_TYPES:
                same_period_vals = line._get_comodel_partner()._l10n_ar_get_period_accumulation(
                    tax=line.tax_id,
                    date=date,
                    exclude_payment=line._l10n_ar_get_payment(),
                )
                same_period_base, same_period_withheld, company_currency = same_period_vals['base'], same_period_vals['withheld'], same_period_vals['currency']
                if ars_currency != company_currency:  # Unlikely, AR companies should use ARS as company currency...
                    same_period_base = company_currency._convert(from_amount=same_period_base, to_currency=ars_currency, company=line.company_id, date=date)
                    same_period_withheld = company_currency._convert(from_amount=same_period_withheld, to_currency=ars_currency, company=line.company_id, date=date)
                net_amount_in_ars += same_period_base

            net_amount_in_ars = max(0, net_amount_in_ars - line.tax_id.l10n_ar_non_taxable_amount)

            if line.tax_id.l10n_ar_withholding_tax_type == 'earnings_scale':
                tax_amount_ars = line.tax_id.l10n_ar_scale_id._l10n_ar_get_tax_amount_from_bracket(net_amount_in_ars)
            else:
                tax_amount_ars = line._l10n_ar_apply_withholding_tax(custom_base_amount=net_amount_in_ars, currency=ars_currency)
            # What was already withheld this month has been levied on that same accumulated base.
            tax_amount_ars -= same_period_withheld
            if line.tax_id.l10n_ar_minimum_threshold > tax_amount_ars:
                tax_amount_ars = 0.0

            line.amount = ars_currency._convert(from_amount=tax_amount_ars, to_currency=line_currency, company=line.company_id, date=date)

        super(AccountWithholdingLine, self - ar_lines)._compute_amount()

    def _l10n_ar_apply_withholding_tax(self, custom_base_amount=None, currency=None):
        """ Return the amount of tax_id over base_amount, as computed by the generic tax engine,
        in the currency of the line or the provided currency.
        """
        self.ensure_one()
        AccountTax = self.env['account.tax']
        base_line = AccountTax._prepare_base_line_for_taxes_computation(
            self,
            tax_ids=self.tax_id,
            price_unit=self.base_amount if custom_base_amount is None else custom_base_amount,
            quantity=1.0,
            currency_id=currency or self.comodel_currency_id,
            partner_id=self._get_comodel_partner(),
            calculate_withholding_taxes=True,
        )
        AccountTax._add_tax_details_in_base_line(base_line, self.company_id)
        AccountTax._round_base_lines_tax_details([base_line], self.company_id)
        return -base_line['tax_details']['taxes_data'][0]['tax_amount_currency']

    def _l10n_ar_get_payment(self):
        """ TO OVERRIDE - Return the payment this line belongs to, when it is already materialized. """
        return self.env['account.payment']
