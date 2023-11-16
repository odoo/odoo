/** @odoo-module **/

import { evaluateExpr, parseExpr } from "./py_js/py";
import { isError } from "@web/core/error";
import { tryEvaluate } from "./py_js/py_interpreter";

/**
 * @typedef {{[key: string]: any}} Context
 * @typedef {Context | string | undefined} ContextDescription
 */

/**
 * Create an evaluated context from an arbitrary list of context representations.
 * The evaluated context in construction is used along the way to evaluate further parts.
 *
 * @param {ContextDescription[]} contexts
 * @param {Context} [initialEvaluationContext] optional evaluation context to start from.
 * @returns {Context}
 */
export function makeContext(contexts, initialEvaluationContext) {
    const evaluationContext = Object.assign({}, initialEvaluationContext);
    const context = {};
    for (let ctx of contexts) {
        if (ctx !== "") {
            ctx = typeof ctx === "string" ? evaluateExpr(ctx, evaluationContext) : ctx;
            Object.assign(context, ctx);
            Object.assign(evaluationContext, context); // is this behavior really wanted ?
        }
    }
    return context;
}

/**
 * Allow to evaluate a context with an incomplete evaluation context. The evaluated context only
 * contains keys whose values are static or can be evaluated with the given evaluation context.
 *
 * @param {string} context
 * @param {Object} [evaluationContext={}]
 * @returns {Context}
 */
export function evalPartialContext(_context, evaluationContext = {}) {
    const ast = parseExpr(_context);
    const context = {};
    for (const key in ast.value) {
        const valueAST = ast.value[key];
        const val = tryEvaluate(valueAST, evaluationContext);
        if (isError(val)) {
            continue;
        }
        context[key] = val;
    }
    return context;
}
