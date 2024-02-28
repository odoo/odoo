/** @odoo-module **/

import { evaluateExpr } from "./py_js/py";

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
