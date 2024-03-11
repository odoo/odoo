/** @odoo-module **/
// @ts-check

import * as spreadsheet from "@odoo/o-spreadsheet";

const { parseTokens, iterateAstNodes } = spreadsheet;

/**
 * @typedef {import("@odoo/o-spreadsheet").AST} AST
 *
 * @typedef {Object} OdooFunctionDescription
 * @property {string} functionName Name of the function
 * @property {Array<AST>} args Arguments of the function
 */

/**
 * This function is used to search for the functions which match the given matcher
 * from the given formula
 *
 * @param {import("@odoo/o-spreadsheet").Token[]} tokens
 * @param {string[]} functionNames e.g. ["ODOO.LIST", "ODOO.LIST.HEADER"]
 * @private
 * @returns {Array<OdooFunctionDescription>}
 */
export function getOdooFunctions(tokens, functionNames) {
    // Parsing is an expensive operation, so we first check if the
    // formula contains one of the function names
    if (!tokens.some((t) => t.type === "SYMBOL" && functionNames.includes(t.value.toUpperCase()))) {
        return [];
    }
    let ast;
    try {
        ast = parseTokens(tokens);
    } catch {
        return [];
    }
    return _getOdooFunctionsFromAST(ast, functionNames);
}

/**
 * Extract the data source id (always the first argument) from the function
 * context of the given token.
 * @param {Token} tokenAtCursor
 * @returns {string | undefined}
 */
export function extractDataSourceId(tokenAtCursor) {
    const idAst = tokenAtCursor.functionContext?.args[0];
    if (!idAst || !["STRING", "NUMBER"].includes(idAst.type)) {
        return;
    }
    return idAst.value;
}

/**
 * This function is used to search for the functions which match the given matcher
 * from the given AST
 *
 * @param {AST} ast
 * @param {string[]} functionNames e.g. ["ODOO.LIST", "ODOO.LIST.HEADER"]
 *
 * @private
 * @returns {Array<OdooFunctionDescription>}
 */
function _getOdooFunctionsFromAST(ast, functionNames) {
    return iterateAstNodes(ast)
        .filter((ast) => ast.type === "FUNCALL" && functionNames.includes(ast.value.toUpperCase()))
        .map((/**@type {import("@odoo/o-spreadsheet").ASTFuncall}*/ ast) => ({
            functionName: ast.value.toUpperCase(),
            args: ast.args,
        }));
}
