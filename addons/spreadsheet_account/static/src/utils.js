/** @odoo-module **/
import { getOdooFunctions } from "@spreadsheet/helpers/odoo_functions_helpers";

/** @typedef  {import("@spreadsheet/helpers/odoo_functions_helpers").OdooFunctionDescription} OdooFunctionDescription*/

/**
 * @param {string} formula
 * @returns {number}
 */
export function getNumberOfAccountFormulas(formula) {
    return getOdooFunctions(formula, (functionName) =>
        ["ODOO.BALANCE", "ODOO.CREDIT", "ODOO.DEBIT"].includes(functionName)
    ).filter((fn) => fn.isMatched).length;
}

/**
 * Get the first Account function description of the given formula.
 *
 * @param {string} formula
 * @returns {OdooFunctionDescription | undefined}
 */
export function getFirstAccountFunction(formula) {
    return getOdooFunctions(formula, (functionName) =>
        ["ODOO.BALANCE", "ODOO.CREDIT", "ODOO.DEBIT"].includes(functionName)
    ).find((fn) => fn.isMatched);
}
