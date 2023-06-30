/** @odoo-module **/

import * as spreadsheet from "@odoo/o-spreadsheet";

const { parse, iterateAstNodes } = spreadsheet;

/**
 * @typedef {Object} OdooFunctionDescription
 * @property {string} functionName Name of the function
 * @property {Array<string>} args Arguments of the function
 */

/**
 * This function is used to search for the functions which match the given matcher
 * from the given formula
 *
 * @param {string} formula
 * @param {string[]} functionNames e.g. ["ODOO.LIST", "ODOO.LIST.HEADER"]
 * @private
 * @returns {Array<OdooFunctionDescription>}
 */
export function getOdooFunctions(formula, functionNames) {
    const formulaUpperCased = formula.toUpperCase();
    // Parsing is an expensive operation, so we first check if the
    // formula contains one of the function names
    if (!functionNames.some((fn) => formulaUpperCased.includes(fn.toUpperCase()))) {
        return [];
    }
    let ast;
    try {
        ast = parse(formula);
    } catch {
        return [];
    }
    return _getOdooFunctionsFromAST(ast, functionNames);
}

/**
 * This function is used to search for the functions which match the given matcher
 * from the given AST
 *
 * @param {Object} ast (see o-spreadsheet)
 * @param {string[]} functionNames e.g. ["ODOO.LIST", "ODOO.LIST.HEADER"]
 *
 * @private
 * @returns {Array<OdooFunctionDescription>}
 */
function _getOdooFunctionsFromAST(ast, functionNames) {
    return iterateAstNodes(ast)
        .filter((ast) => ast.type === "FUNCALL" && functionNames.includes(ast.value.toUpperCase()))
        .map((ast) => ({ functionName: ast.value.toUpperCase(), args: ast.args }));
}
