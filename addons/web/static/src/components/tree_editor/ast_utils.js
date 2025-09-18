// @ts-check

/** @module @web/components/tree_editor/ast_utils - AST manipulation helpers for boolean wrapping, negation, and path validation */

/** @import { AST } from "@web/core/py_js/py_parser" */

import { COMPARATORS, TERM_OPERATORS_NEGATION_EXTENDED } from "./operators";

/**
 * @param {AST} ast
 * @returns {boolean} whether the AST is a `bool(...)` call
 */
export function isBool(ast) {
    return (
        ast.type === 8 &&
        ast.fn.type === 5 &&
        ast.fn.value === "bool" &&
        ast.args.length === 1
    );
}

/**
 * @param {AST} ast
 * @returns {boolean} whether the AST is a `not` unary expression
 */
export function isNot(ast) {
    return ast.type === 6 && ast.op === "not";
}

/**
 * Negate an AST node. Unwraps double negations and flips comparison operators.
 * @param {AST} ast
 * @returns {AST} negated AST
 */
export function not(ast) {
    if (isNot(ast)) {
        return ast.right;
    }
    if (ast.type === 2) {
        return { ...ast, value: !ast.value };
    }
    if (ast.type === 7 && COMPARATORS.includes(ast.op)) {
        return { ...ast, op: TERM_OPERATORS_NEGATION_EXTENDED[ast.op] }; // do not use this if ast is within a domain context!
    }
    return { type: 6, op: "not", right: isBool(ast) ? ast.args[0] : ast };
}

/**
 * @param {AST} ast
 * @param {{ getFieldDef?: (name: string) => (Object|null) }} options
 * @returns {boolean} whether the AST represents a valid field path
 */
export function isValidPath(ast, options) {
    const getFieldDef = options.getFieldDef || (() => null);
    if (ast.type === 5) {
        return getFieldDef(ast.value) !== null;
    }
    return false;
}
