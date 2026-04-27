import { patch } from "@web/core/utils/patch";
import { accountTaxHelpers } from "@account/helpers/account_tax";

patch(accountTaxHelpers, {
    // EXTENDS 'account'
    prepare_base_line_for_taxes_computation(record, kwargs = {}) {
        const base_line = super.prepare_base_line_for_taxes_computation(record, kwargs);
        base_line.l10n_it_epson_printer = kwargs.l10n_it_epson_printer || false;
        return base_line;
    },

    // EXTENDS 'account'
    add_tax_details_in_base_line(base_line, company, { rounding_method = null } = {}) {
        if (
            base_line.l10n_it_epson_printer &&
            !base_line.special_mode &&
            base_line.tax_ids.length === 1 &&
            base_line.tax_ids[0].amount_type === "percent" &&
            !base_line.tax_ids[0].price_include
        ) {
            let new_base_line = this.prepare_base_line_for_taxes_computation(base_line, {
                quantity: 1.0,
                discount: 0.0,
            });
            super.add_tax_details_in_base_line(new_base_line, company, {
                rounding_method: rounding_method,
            });
            this.round_base_lines_tax_details([new_base_line], company);
            let tax_details = new_base_line.tax_details;
            const price_unit_included = tax_details.total_included_currency;
            new_base_line = this.prepare_base_line_for_taxes_computation(base_line, {
                price_unit: price_unit_included,
                special_mode: "total_included",
            });
            super.add_tax_details_in_base_line(new_base_line, company, {
                rounding_method: rounding_method,
            });
            this.round_base_lines_tax_details([new_base_line], company);
            tax_details = new_base_line.tax_details;
            base_line.manual_tax_amounts = {};
            for (const tax_data of tax_details.taxes_data) {
                base_line.manual_tax_amounts[tax_data.tax.id.toString()] = {
                    tax_amount_currency: tax_data.tax_amount_currency,
                    base_amount_currency: tax_data.base_amount_currency,
                };
            }
        }
        super.add_tax_details_in_base_line(base_line, company, {
            rounding_method: rounding_method,
        });
    },
});
