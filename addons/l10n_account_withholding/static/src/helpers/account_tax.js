import { patch } from "@web/core/utils/patch";
import { accountTaxHelpers } from "@account/helpers/account_tax";

patch(accountTaxHelpers, {
    /** override **/
    batch_for_taxes_computation(taxes, { special_mode = null } = {}) {
        // We do not have front-end use cases where the withholding tax should be handled.
        taxes = taxes.filter((tax) => !tax.is_withholding_tax_on_payment);
        return super.batch_for_taxes_computation(taxes, {
            special_mode: special_mode,
        });
    },
});
