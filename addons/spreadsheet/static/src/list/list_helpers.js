/** @odoo-module */

import { getOdooFunctions } from "../helpers/odoo_functions_helpers";

/**
 * Parse a spreadsheet formula and detect the number of LIST functions that are
 * present in the given formula.
 *
 * @param {string} formula
 *
 * @returns {number}
 */
export function getNumberOfListFormulas(formula) {
    return getOdooFunctions(formula, ["ODOO.LIST", "ODOO.LIST.HEADER"]).filter((fn) => fn.isMatched)
        .length;
}

/**
 * Get the first List function description of the given formula.
 *
 * @param {string} formula
 *
 * @returns {import("../helpers/odoo_functions_helpers").OdooFunctionDescription|undefined}
 */
export function getFirstListFunction(formula) {
    return getOdooFunctions(formula, ["ODOO.LIST", "ODOO.LIST.HEADER"]).find((fn) => fn.isMatched);
}
