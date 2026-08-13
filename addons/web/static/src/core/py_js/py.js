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
    let ast;
    try {
        ast = parseExpr(expr);
    } catch (error) {
        throw new EvalError(`Can not parse python expression: (${expr})\nError: ${error.message}`);
    }
    try {
        return evaluate(ast, context);
    } catch (error) {
        throw new EvalError(`Can not evaluate python expression: (${expr})\nError: ${error.message}`);
    }
}

/**
 * Evaluates a python expression to return a boolean.
 *
 * @param {string} expr
 * @param {Object} [context]
 * @returns {any}
 */
export function evaluateBooleanExpr(expr, context = {}) {
    if (!expr || expr === 'False' || expr === '0') {
        return false;
    }
    if (expr === 'True' || expr === '1') {
        return true;
    }
    return evaluateExpr(`bool(${expr})`, context);
}
