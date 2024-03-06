import { patch } from "@web/core/utils/patch";

import { accountTaxHelpers } from "@account/helpers/account_tax";
import { evaluateExpr } from "@web/core/py_js/py";

// -------------------------------------------------------------------------
// HELPERS IN BOTH PYTHON/JAVASCRIPT (account_tax.js / account_tax.py)
// -------------------------------------------------------------------------

patch(accountTaxHelpers, {
    /** override **/
    process_as_fixed_tax_amount_batch(batch) {
        return batch.amount_type === "code" || super.process_as_fixed_tax_amount_batch(...arguments);
    },

    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     */
    eval_tax_amount_formula(tax_values, evaluation_context) {
        const raw_base =
            evaluation_context.quantity * evaluation_context.price_unit +
            evaluation_context.extra_base;
        const formula_context = {
            price_unit: evaluation_context.price_unit,
            quantity: evaluation_context.quantity,
            product: evaluation_context.product,
            base: raw_base,
        };
        return evaluateExpr(tax_values._js_formula, formula_context);
    },

    /** override **/
    eval_tax_amount(tax_values, evaluation_context) {
        if (tax_values.amount_type === "code") {
            return this.eval_tax_amount_formula(tax_values, evaluation_context);
        }
        return super.eval_tax_amount(...arguments);
    },
});
