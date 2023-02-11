/** @odoo-module **/

import { evaluate } from "./py_interpreter";
import { parse } from "./py_parser";
import { tokenize } from "./py_tokenizer";

export { evaluate } from "./py_interpreter";
export { parse } from "./py_parser";
export { tokenize } from "./py_tokenizer";
export { formatAST } from "./py_utils";

/**
 * @typedef { import("./py_tokenizer").Token } Token
 * @typedef { import("./py_parser").AST } AST
 */

/**
 * Parses an expression into a valid AST representation
 
 * @param {string} expr 
 * @returns { AST }
 */
export function parseExpr(expr) {
    const tokens = tokenize(expr);
    return parse(tokens);
}

/**
 * Evaluates a python expression
 *
 * @param {string} expr
 * @param {Object} [context]
 * @returns {any}
 */
export function evaluateExpr(expr, context = {}) {
    const ast = parseExpr(expr);
    return evaluate(ast, context);
}
