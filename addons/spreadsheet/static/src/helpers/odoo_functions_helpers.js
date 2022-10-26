/** @odoo-module **/

import spreadsheet from "../o_spreadsheet/o_spreadsheet_extended";

const { parse } = spreadsheet;

/**
 * @typedef {Object} OdooFunctionDescription
 * @property {string} functionName Name of the function
 * @property {Array<string>} args Arguments of the function
 * @property {boolean} isMatched True if the function is matched by the matcher function
 */

/**
 * This function is used to search for the functions which match the given matcher
 * from the given formula
 *
 * @param {string} formula
 * @param {Function} matcher a predicate that matches a function name
 * @private
 * @returns {Array<OdooFunctionDescription>}
 */
export function getOdooFunctions(formula, matcher) {
    let ast;
    try {
        ast = parse(formula);
    } catch (_) {
        return [];
    }
    return _getOdooFunctionsFromAST(ast, matcher);
}

/**
 * This function is used to search for the functions which match the given matcher
 * from the given AST
 *
 * @param {Object} ast (see o-spreadsheet)
 * @param {Function} matcher a predicate that matches a function name
 *
 * @private
 * @returns {Array<OdooFunctionDescription>}
 */
function _getOdooFunctionsFromAST(ast, matcher) {
    switch (ast.type) {
        case "UNARY_OPERATION":
            return _getOdooFunctionsFromAST(ast.operand, matcher);
        case "BIN_OPERATION": {
            return _getOdooFunctionsFromAST(ast.left, matcher).concat(
                _getOdooFunctionsFromAST(ast.right, matcher)
            );
        }
        case "FUNCALL": {
            const functionName = ast.value.toUpperCase();

            if (matcher(functionName)) {
                return [{ functionName, args: ast.args, isMatched: true }];
            } else {
                return ast.args.map((arg) => _getOdooFunctionsFromAST(arg, matcher)).flat();
            }
        }
        default:
            return [];
    }
}
