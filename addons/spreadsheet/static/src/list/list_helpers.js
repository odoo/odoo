// @ts-check


/**
 * @typedef {import("@odoo/o-spreadsheet").CompiledFormula} CompiledFormula
 * @typedef {import("@odoo/o-spreadsheet").CoreGetters} CoreGetters
 * @typedef  {import("../helpers/odoo_functions_helpers").OdooFunctionDescription} OdooFunctionDescription
 * */

const ALL_LIST_FUNCTIONS = ["ODOO.LIST", "ODOO.LIST.HEADER"];

/**
 * Parse a spreadsheet formula and detect the number of LIST functions that are
 * present in the given formula.
 *
 * @param {CompiledFormula} compiledFormula
 *
 * @returns {boolean}
 */
export function hasListFormula(compiledFormula) {
    return ALL_LIST_FUNCTIONS.some(funcName => compiledFormula.usesSymbol(funcName));
}

/**
 * Get the first List function description of the given formula.
 *
 * @param {CompiledFormula} compiledFormula
 * @param {CoreGetters} getters
 *
 * @returns {OdooFunctionDescription|undefined}
 */
export function getFirstListFunction(compiledFormula, getters) {
    return compiledFormula.getFunctionsFromTokens( ALL_LIST_FUNCTIONS, getters)[0];
}
