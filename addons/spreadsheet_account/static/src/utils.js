/** @odoo-module **/
import { getOdooFunctions } from "@spreadsheet/helpers/odoo_functions_helpers";

/** @typedef  {import("@spreadsheet/helpers/odoo_functions_helpers").OdooFunctionDescription} OdooFunctionDescription*/

/**
 * @param {string} formula
 * @returns {number}
 */
export function getNumberOfAccountFormulas(formula) {
    return getOdooFunctions(formula, ["ODOO.BALANCE", "ODOO.CREDIT", "ODOO.DEBIT"]).filter(
        (fn) => fn.isMatched
    ).length;
}

/**
 * Get the first Account function description of the given formula.
 *
 * @param {string} formula
 * @returns {OdooFunctionDescription | undefined}
 */
export function getFirstAccountFunction(formula) {
    return getOdooFunctions(formula, ["ODOO.BALANCE", "ODOO.CREDIT", "ODOO.DEBIT"]).find(
        (fn) => fn.isMatched
    );
}
