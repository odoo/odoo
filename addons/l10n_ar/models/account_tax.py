from odoo import api, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    @api.model
    def _round_tax_details_tax_amounts(self, base_lines, company, mode='mixed'):
        # EXTENDS 'account'
        country_code = company.account_fiscal_country_id.code
        if country_code == 'AR':
            mode = 'excluded'

        super()._round_tax_details_tax_amounts(base_lines, company, mode=mode)

        if country_code != 'AR':
            return

        company_currency = company.currency_id

        def grouping_function(base_line, tax_data):
            if not tax_data:
                return
            return {
                'tax': tax_data['tax'],
                'currency': base_line['currency_id'],
                'is_refund': base_line['is_refund'],
                'is_reverse_charge': tax_data['is_reverse_charge'],
                'price_include': tax_data['price_include'],
                'rate': base_line['rate'],
            }

        base_lines_aggregated_values = self._aggregate_base_lines_tax_details(base_lines, grouping_function)
        values_per_grouping_key = self._aggregate_base_lines_aggregated_values(base_lines_aggregated_values)
        for grouping_key, values in values_per_grouping_key.items():
            if (
                not grouping_key
                or grouping_key['currency'] == company_currency
                or not grouping_key['rate']
            ):
                continue

            # Tax amount.
            current_total_tax_amount = values['tax_amount']
            expected_total_tax_amount = company_currency.round(values['tax_amount_currency'] / grouping_key['rate'])
            delta_total_tax_amount = expected_total_tax_amount - current_total_tax_amount

            if not company_currency.is_zero(delta_total_tax_amount):
                target_factors = [
                    {
                        'factor': tax_data['tax_amount'],
                        'tax_data': tax_data,
                    }
                    for _base_line, taxes_data in values['base_line_x_taxes_data']
                    for tax_data in taxes_data
                ]
                amounts_to_distribute = self._distribute_delta_amount_smoothly(
                    precision_digits=company_currency.decimal_places,
                    delta_amount=delta_total_tax_amount,
                    target_factors=target_factors,
                )
                for target_factor, amount_to_distribute in zip(target_factors, amounts_to_distribute):
                    tax_data = target_factor['tax_data']
                    tax_data['tax_amount'] += amount_to_distribute

            # Base amount.
            current_total_base_amount = values['base_amount']
            expected_total_base_amount = company_currency.round(values['base_amount_currency'] / grouping_key['rate'])
            delta_total_base_amount = expected_total_base_amount - current_total_base_amount

            if not company_currency.is_zero(delta_total_base_amount):
                target_factors = [
                    {
                        'factor': tax_data['base_amount'],
                        'tax_data': tax_data,
                    }
                    for _base_line, taxes_data in values['base_line_x_taxes_data']
                    for tax_data in taxes_data
                ]
                amounts_to_distribute = self._distribute_delta_amount_smoothly(
                    precision_digits=company_currency.decimal_places,
                    delta_amount=delta_total_base_amount,
                    target_factors=target_factors,
                )
                for target_factor, amount_to_distribute in zip(target_factors, amounts_to_distribute):
                    tax_data = target_factor['tax_data']
                    tax_data['base_amount'] += amount_to_distribute

    @api.model
    def _round_tax_details_base_lines(self, base_lines, company, mode='mixed'):
        # EXTENDS 'account'
        country_code = company.account_fiscal_country_id.code
        if country_code == 'AR':
            mode = 'excluded'

        super()._round_tax_details_base_lines(base_lines, company, mode=mode)

        if country_code != 'AR':
            return

        company_currency = company.currency_id

        def grouping_function(base_line, tax_data):
            return {
                'currency': base_line['currency_id'],
                'is_refund': base_line['is_refund'],
                'rate': base_line['rate'],
            }

        base_lines_aggregated_values = self._aggregate_base_lines_tax_details(base_lines, grouping_function)
        values_per_grouping_key = self._aggregate_base_lines_aggregated_values(base_lines_aggregated_values)
        for grouping_key, values in values_per_grouping_key.items():
            if (
                not grouping_key
                or grouping_key['currency'] == company_currency
                or not grouping_key['rate']
            ):
                continue

            current_total_base_amount = values['total_excluded']
            expected_total_base_amount = company_currency.round(values['total_excluded_currency'] / grouping_key['rate'])
            delta_total_base_amount = expected_total_base_amount - current_total_base_amount

            target_factors = [
                {
                    'factor': base_line['tax_details']['raw_total_excluded'],
                    'base_line': base_line,
                }
                for base_line, _taxes_data in values['base_line_x_taxes_data']
            ]
            amounts_to_distribute = self._distribute_delta_amount_smoothly(
                precision_digits=company_currency.decimal_places,
                delta_amount=delta_total_base_amount,
                target_factors=target_factors,
            )
            for target_factor, amount_to_distribute in zip(target_factors, amounts_to_distribute):
                base_line = target_factor['base_line']
                base_line['tax_details']['delta_total_excluded'] += amount_to_distribute
