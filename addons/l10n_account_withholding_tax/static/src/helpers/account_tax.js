import { patch } from "@web/core/utils/patch";
import { accountTaxHelpers } from "@account/helpers/account_tax";

patch(accountTaxHelpers, {
    /** override **/
    add_tax_details_in_base_line(base_line, company, { rounding_method = null } = {}) {
        if (!base_line.calculate_withholding_taxes) {
            base_line.filter_tax_function = t => !t.is_withholding_tax_on_payment;
        }
        super.add_tax_details_in_base_line(base_line, company, {rounding_method: rounding_method});
    },
});
