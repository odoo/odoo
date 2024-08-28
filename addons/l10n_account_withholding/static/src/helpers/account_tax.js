import { patch } from "@web/core/utils/patch";
import { accountTaxHelpers } from "@account/helpers/account_tax";

patch(accountTaxHelpers, {
    /** override **/
    add_tax_details_in_base_line(base_line, company, { rounding_method = null } = {}) {
        if (base_line.calculate_withholding_taxes) {
            super.add_tax_details_in_base_line(base_line, company, {rounding_method: rounding_method});
            return;
        }

        const taxes = this.flatten_taxes_and_sort_them(base_line.tax_ids).sorted_taxes.filter((tax) => tax.is_withholding_tax_on_payment);
        if (!taxes.length) {
            super.add_tax_details_in_base_line(base_line, company, {rounding_method: rounding_method});
            return;
        }

        // Neutralize the taxes that are withholding for forcing a manual tax amounts for them.
        const manual_tax_amounts = { ... base_line.manual_tax_amounts || {}};
        for (const tax of taxes) {
            manual_tax_amounts[tax.id.toString()] = { tax_amount_currency: 0.0};
        }
        const new_base_line = this.prepare_base_line_for_taxes_computation(base_line, {
            manual_tax_amounts: manual_tax_amounts,
        });
        super.add_tax_details_in_base_line(new_base_line, company, {rounding_method: rounding_method});

        // Push the new tax_details into the original base_line.
        delete new_base_line.manual_tax_amounts;
        const tax_details = new_base_line.tax_details;
        base_line.tax_details = tax_details;
        tax_details.taxes_data = tax_details.taxes_data.filter((tax_data) => !tax_data.tax.is_withholding_tax_on_payment);
    },
});
