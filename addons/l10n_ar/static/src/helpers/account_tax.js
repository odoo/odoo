import { floatIsZero, roundPrecision } from "@web/core/utils/numbers";
import { patch } from "@web/core/utils/patch";

import { accountTaxHelpers } from "@account/helpers/account_tax";

// -------------------------------------------------------------------------
// HELPERS IN BOTH PYTHON/JAVASCRIPT (account_tax.js / account_tax.py)
// -------------------------------------------------------------------------

patch(accountTaxHelpers, {
    // EXTENDS 'account'
    round_tax_details_tax_amounts(base_lines, company, { mode = "mixed" } = {}) {
        const country_code = company.account_fiscal_country_id.code;
        if (country_code === "AR") {
            mode = "excluded";
        }

        super.round_tax_details_tax_amounts(base_lines, company, { mode: mode });

        if (country_code !== "AR") {
            return;
        }

        const company_currency = company.currency_id;

        function grouping_function(base_line, tax_data) {
            if (!tax_data) {
                return;
            }
            return {
                tax: tax_data.tax,
                currency: base_line.currency_id,
                is_refund: base_line.is_refund,
                is_reverse_charge: tax_data.is_reverse_charge,
                price_include: tax_data.price_include,
                rate: base_line.rate,
            };
        }

        const base_lines_aggregated_values = this.aggregate_base_lines_tax_details(
            base_lines,
            grouping_function
        );
        const values_per_grouping_key = this.aggregate_base_lines_aggregated_values(
            base_lines_aggregated_values
        );
        for (const values of Object.values(values_per_grouping_key)) {
            const grouping_key = values.grouping_key;
            if (!grouping_key || grouping_key.currency === company_currency || !grouping_key.rate) {
                continue;
            }

            // Tax amount
            const current_total_tax_amount = values.tax_amount;
            const expected_total_tax_amount = roundPrecision(
                values.tax_amount_currency / grouping_key.rate,
                company_currency.rounding
            );
            const delta_total_tax_amount = expected_total_tax_amount - current_total_tax_amount;

            if (!floatIsZero(delta_total_tax_amount, company_currency.decimal_places)) {
                const target_factors = values.base_line_x_taxes_data.flatMap(([_, taxes_data]) =>
                    taxes_data.map((tax_data) => ({
                        factor: tax_data.tax_amount,
                        tax_data: tax_data,
                    }))
                );
                const amounts_to_distribute = this.distribute_delta_amount_smoothly(
                    company_currency.decimal_places,
                    delta_total_tax_amount,
                    target_factors
                );
                for (let i = 0; i < target_factors.length; i++) {
                    const tax_data = target_factors[i].tax_data;
                    const amount_to_distribute = amounts_to_distribute[i];
                    tax_data.tax_amount += amount_to_distribute;
                }
            }

            // Base amount
            const current_total_base_amount = values.base_amount;
            const expected_total_base_amount = roundPrecision(
                values.base_amount_currency / grouping_key.rate,
                company_currency.rounding
            );
            const delta_total_base_amount = expected_total_base_amount - current_total_base_amount;

            if (!floatIsZero(delta_total_base_amount, company_currency.decimal_places)) {
                const target_factors = values.base_line_x_taxes_data.flatMap(([_, taxes_data]) =>
                    taxes_data.map((tax_data) => ({
                        factor: tax_data.base_amount,
                        tax_data: tax_data,
                    }))
                );
                const amounts_to_distribute = this.distribute_delta_amount_smoothly(
                    company_currency.decimal_places,
                    delta_total_base_amount,
                    target_factors
                );
                for (let i = 0; i < target_factors.length; i++) {
                    const tax_data = target_factors[i].tax_data;
                    const amount_to_distribute = amounts_to_distribute[i];
                    tax_data.base_amount += amount_to_distribute;
                }
            }
        }
    },

    // EXTENDS 'account'
    round_tax_details_base_lines(base_lines, company, { mode = "mixed" } = {}) {
        const country_code = company.account_fiscal_country_id.code;
        if (country_code === "AR") {
            mode = "excluded";
        }

        super.round_tax_details_base_lines(base_lines, company, { mode: mode });

        if (country_code !== "AR") {
            return;
        }

        const company_currency = company.currency_id;

        function grouping_function(base_line, tax_data) {
            if (!tax_data) {
                return;
            }
            return {
                currency: base_line.currency_id,
                is_refund: base_line.is_refund,
                rate: base_line.rate,
            };
        }

        const base_lines_aggregated_values = this.aggregate_base_lines_tax_details(
            base_lines,
            grouping_function
        );
        const values_per_grouping_key = this.aggregate_base_lines_aggregated_values(
            base_lines_aggregated_values
        );
        for (const values of Object.values(values_per_grouping_key)) {
            const grouping_key = values.grouping_key;
            if (!grouping_key || grouping_key.currency === company_currency || !grouping_key.rate) {
                continue;
            }

            const current_total_base_amount = values.total_excluded;
            const expected_total_base_amount = roundPrecision(
                values.total_excluded_currency / grouping_key.rate,
                company_currency.rounding
            );
            const delta_total_base_amount = expected_total_base_amount - current_total_base_amount;

            const target_factors = values.base_line_x_taxes_data.map(([base_line]) => ({
                factor: base_line.tax_details.raw_total_excluded,
                base_line: base_line,
            }));
            const amounts_to_distribute = this.distribute_delta_amount_smoothly(
                company_currency.decimal_places,
                delta_total_base_amount,
                target_factors
            );
            for (let i = 0; i < target_factors.length; i++) {
                const base_line = target_factors[i].base_line;
                const amount_to_distribute = amounts_to_distribute[i];
                base_line.tax_details.delta_total_excluded += amount_to_distribute;
            }
        }
    },
});
