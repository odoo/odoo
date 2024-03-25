/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { TestsSharedJsPython } from "@account/components/tests_shared_js_python/tests_shared_js_python";
import { accountTaxHelpers } from "@account/helpers/account_tax";

patch(TestsSharedJsPython.prototype, {
    /** override **/
    processTest(params){
        if(params.test === "l10n_in_hsn_summary"){
            return accountTaxHelpers.l10n_in_get_hsn_summary_table(params.base_lines, params.display_uom);
        }
        return super.processTest(...arguments);
    },
});
