/** @odoo-module */

import { getOdooFunctions } from "../helpers/odoo_functions_helpers";

/** @typedef {import("@spreadsheet/helpers/odoo_functions_helpers").Token} Token */

/**
 * Parse a spreadsheet formula and detect the number of LIST functions that are
 * present in the given formula.
 *
 * @param {Token[]} tokens
 *
 * @returns {number}
 */
export function getNumberOfListFormulas(tokens) {
    return getOdooFunctions(tokens, ["ODOO.LIST", "ODOO.LIST.HEADER"]).length;
}

/**
 * Get the first List function description of the given formula.
 *
 * @param {Token[]} tokens
 *
 * @returns {import("../helpers/odoo_functions_helpers").OdooFunctionDescription|undefined}
 */
export function getFirstListFunction(tokens) {
    return getOdooFunctions(tokens, ["ODOO.LIST", "ODOO.LIST.HEADER"])[0];
}
