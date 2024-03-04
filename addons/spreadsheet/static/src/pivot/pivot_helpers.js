/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { getOdooFunctions } from "../helpers/odoo_functions_helpers";

/** @typedef {import("@spreadsheet/helpers/odoo_functions_helpers").Token} Token */

export const pivotFormulaRegex = /^=.*PIVOT/;

//--------------------------------------------------------------------------
// Public
//--------------------------------------------------------------------------

/**
 * Parse a spreadsheet formula and detect the number of PIVOT functions that are
 * present in the given formula.
 *
 * @param {Token[]} tokens
 *
 * @returns {number}
 */
export function getNumberOfPivotFormulas(tokens) {
    return getOdooFunctions(tokens, [
        "ODOO.PIVOT",
        "ODOO.PIVOT.HEADER",
        "ODOO.PIVOT.POSITION",
        "ODOO.PIVOT.TABLE",
    ]).length;
}

/**
 * Get the first Pivot function description of the given formula.
 *
 * @param {Token[]} tokens
 *
 * @returns {import("../helpers/odoo_functions_helpers").OdooFunctionDescription|undefined}
 */
export function getFirstPivotFunction(tokens) {
    return getOdooFunctions(tokens, [
        "ODOO.PIVOT",
        "ODOO.PIVOT.HEADER",
        "ODOO.PIVOT.POSITION",
        "ODOO.PIVOT.TABLE",
    ])[0];
}

/**
 * Build a pivot formula expression
 *
 * @param {string} formula formula to be used (PIVOT or PIVOT.HEADER)
 * @param {*} args arguments of the formula
 *
 * @returns {string}
 */
export function makePivotFormula(formula, args) {
    return `=${formula}(${args
        .map((arg) => {
            const stringIsNumber =
                typeof arg == "string" && !isNaN(arg) && Number(arg).toString() === arg;
            const convertToNumber = typeof arg == "number" || stringIsNumber;
            return convertToNumber ? `${arg}` : `"${arg.toString().replace(/"/g, '\\"')}"`;
        })
        .join(",")})`;
}

export const PERIODS = {
    day: _t("Day"),
    week: _t("Week"),
    month: _t("Month"),
    quarter: _t("Quarter"),
    year: _t("Year"),
};
