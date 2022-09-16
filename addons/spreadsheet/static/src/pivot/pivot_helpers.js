/** @odoo-module **/

import { _t } from "web.core";
import { FORMATS } from "../helpers/constants";
import { getOdooFunctions } from "../helpers/odoo_functions_helpers";

export const pivotFormulaRegex = /^=.*PIVOT/;

//--------------------------------------------------------------------------
// Public
//--------------------------------------------------------------------------

/**
 * Format a data
 *
 * @param {string} interval aggregate interval i.e. month, week, quarter, ...
 * @param {string} value
 */
export function formatDate(interval, value) {
    const output = FORMATS[interval].display;
    const input = FORMATS[interval].out;
    const date = moment(value, input);
    return date.isValid() ? date.format(output) : _t("None");
}

/**
 * Parse a spreadsheet formula and detect the number of PIVOT functions that are
 * present in the given formula.
 *
 * @param {string} formula
 *
 * @returns {number}
 */
export function getNumberOfPivotFormulas(formula) {
    return getOdooFunctions(formula, (functionName) =>
        ["ODOO.PIVOT", "ODOO.PIVOT.HEADER", "ODOO.PIVOT.POSITION"].includes(functionName)
    ).filter((fn) => fn.isMatched).length;
}

/**
 * Get the first Pivot function description of the given formula.
 *
 * @param {string} formula
 *
 * @returns {import("../helpers/odoo_functions_helpers").OdooFunctionDescription|undefined}
 */
export function getFirstPivotFunction(formula) {
    return getOdooFunctions(formula, (functionName) =>
        ["ODOO.PIVOT", "ODOO.PIVOT.HEADER", "ODOO.PIVOT.POSITION"].includes(functionName)
    ).find((fn) => fn.isMatched);
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
        .map((arg) =>
            typeof arg == "number" || (typeof arg == "string" && !isNaN(arg))
                ? `${arg}`
                : `"${arg.toString().replace(/"/g, '\\"')}"`
        )
        .join(",")})`;
}

export const PERIODS = {
    day: _t("Day"),
    week: _t("Week"),
    month: _t("Month"),
    quarter: _t("Quarter"),
    year: _t("Year"),
};
