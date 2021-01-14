/** @odoo-module **/

import { tokenize } from "./tokenizer";
import { parse } from "./parser";
import { evaluate } from "./interpreter";
export { tokenize } from "./tokenizer";
export { parse } from "./parser";
export { evaluate } from "./interpreter";
export { formatAST } from "./utils";

/**
 * @typedef { import("./tokenizer").Token } Token
 * @typedef { import("./parser").AST } AST
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
 * @param {Object} context
 * @returns {any}
 */
export function evaluateExpr(expr, context) {
  const ast = parseExpr(expr);
  return evaluate(ast, context);
}
