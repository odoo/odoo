/** @odoo-module **/
import { getOdooFunctions } from "@spreadsheet/helpers/odoo_functions_helpers";

/**
 * @typedef {import("@spreadsheet/helpers/odoo_functions_helpers").Token} Token
 * @typedef  {import("@spreadsheet/helpers/odoo_functions_helpers").OdooFunctionDescription} OdooFunctionDescription
 */

/**
 * @param {Token[]} tokens
 * @returns {number}
 */
export function getNumberOfAccountFormulas(tokens) {
    return getOdooFunctions(tokens, ["ODOO.BALANCE", "ODOO.CREDIT", "ODOO.DEBIT"]).length;
}

/**
 * Get the first Account function description of the given formula.
 *
 * @param {Token[]} tokens
 * @returns {OdooFunctionDescription | undefined}
 */
export function getFirstAccountFunction(tokens) {
    return getOdooFunctions(tokens, ["ODOO.BALANCE", "ODOO.CREDIT", "ODOO.DEBIT"])[0];
}
