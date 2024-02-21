/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { TestsSharedJsPython } from "@account/components/tests_shared_js_python/tests_shared_js_python";
import { l10n_in_get_hsn_summary_table } from "@l10n_in/helpers/hsn_summary";

patch(TestsSharedJsPython.prototype, {
    /** override **/
    processTest(params){
        if(params.test === "l10n_in_hsn_summary"){
            return l10n_in_get_hsn_summary_table(params.base_lines, params.display_uom);
        }
        return super.processTest(...arguments);
    },
});
