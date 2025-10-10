import { patch } from "@web/core/utils/patch";

import { accountTaxHelpers } from "@account/helpers/account_tax";
import { evaluateExpr } from "@web/core/py_js/py";

// -------------------------------------------------------------------------
// HELPERS IN BOTH PYTHON/JAVASCRIPT (account_tax.js / account_tax.py)
// -------------------------------------------------------------------------

patch(accountTaxHelpers, {
    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     */
    eval_tax_amount_formula(tax, raw_base, evaluation_context) {
        const formula_context = {
            price_unit: evaluation_context.price_unit,
            quantity: evaluation_context.quantity,
            product: evaluation_context.product,
            base: raw_base,
        };
        return evaluateExpr(tax.formula_decoded_info.js_formula, formula_context);
    },

    // EXTENDS 'account'
    eval_tax_amount_fixed_amount(tax, batch, raw_base, evaluation_context) {
        if (tax.amount_type === "code") {
            return this.eval_tax_amount_formula(tax, raw_base, evaluation_context);
        }
        return super.eval_tax_amount_fixed_amount(...arguments);
    },
});
