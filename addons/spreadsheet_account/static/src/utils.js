// @ts-check

/**
 * @typedef {import("@odoo/o-spreadsheet").CompiledFormula} CompiledFormula
 * @typedef {import("@odoo/o-spreadsheet").CoreGetters} CoreGetters
 * @typedef  {import("@spreadsheet/helpers/odoo_functions_helpers").OdooFunctionDescription} OdooFunctionDescription
 */

const ALL_ACCOUNTING_FUNCTIONS = ["ODOO.BALANCE", "ODOO.CREDIT", "ODOO.DEBIT", "ODOO.RESIDUAL", "ODOO.PARTNER.BALANCE", "ODOO.BALANCE.TAG"];

/**
 * @param {CompiledFormula} compiledFormula
 * @returns {boolean}
 */
export function hasAccountingFormula(compiledFormula) {
    return ALL_ACCOUNTING_FUNCTIONS.some(x=>    compiledFormula.usesSymbol(x));
}

/**
 * Get the first Account function description of the given formula.
 *
 * @param {CompiledFormula} compiledFormula
 * @param {CoreGetters} getters
 * @returns {OdooFunctionDescription | undefined}
 */
export function getFirstAccountFunction(compiledFormula, getters) {
    return compiledFormula.getFunctionsFromTokens(ALL_ACCOUNTING_FUNCTIONS, getters)[0];
}
