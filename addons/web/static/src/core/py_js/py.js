/** @odoo-module **/

import { evaluate } from "./py_interpreter";
import { parse } from "./py_parser";
import { tokenize } from "./py_tokenizer";

export { evaluate } from "./py_interpreter";
export { parse } from "./py_parser";
export { tokenize } from "./py_tokenizer";
export { formatAST } from "./py_utils";

// predefined symbols for evaluating attributes (invisible, readonly...)
const IGNORED_IN_EXPRESSION = [
    'True', 'False', 'None',
    'self',
    'uid',
    'context',
    'context_today',
    'active_id',
    'active_ids',
    'allowed_company_ids',
    'current_company_id',
    'active_model',
    'time',
    'datetime',
    'relativedelta',
    'current_date',
    'today',
    'now',
    'abs',
    'len',
    'bool',
    'float',
    'str',
    'unicode',
];

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
 * Return all field name used by this expression
 * eg: expression = '''(
 *      id in [1, 2, 3]
 *      and field_a in parent.truc.id
 *      and field_b in context.get('b')
 *      or (True and bool(context.get('c')))
 *  )
 *  returns {'parent', 'parent.truc', 'parent.truc.id'}
 *
 * @param {string} expr
 * @returns {array}
 */
export function getExpressionFieldNames(expr) {
    if (!expr || expr === 'False' || expr === '0' || expr === 'True' || expr === '1') {
        return [];
    }
    let ast;
    try {
        ast = parseExpr(expr);
    } catch (error) {
        throw new EvalError(`Can not parse python expression: (${expr})\nError: ${error.message}`);
    }
    const getFields = function(ast) {
        if (ast.type === 5) {
            if (!IGNORED_IN_EXPRESSION.includes(ast.value.split('.')[0])) {
                return [ast.value];
            }
            return [];
        }
        if (ast.type === 15) {
            return getFields(ast.obj).map(name => `${name}.${ast.key}`);
        }
        const names = [];
        for (const value of Object.values(ast)) {
            if (value && typeof value === 'object') {
                names.push.apply(names, getFields(value));
            }
        }
        return names;
    }
    const names = getFields(ast);
    if (names.includes("parent")) {
        names.splice(names.indexOf("parent"), 1);
    }
    return names;
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
