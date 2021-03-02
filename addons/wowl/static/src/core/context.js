/** @odoo-module **/

import { evaluateExpr } from "../py_js/index";

/**
 * @typedef {{[key: string]: any}} Context
 * @typedef {Context | string | undefined} ContextDescription
 */

/**
 * Create an evaluated context from an arbitrary list of context representations
 *
 * @param  {...ContextDescription} contexts
 * @returns {Context}
 */
export function makeContext(...contexts) {
  let context = {};
  for (let ctx of contexts) {
    const subCtx = typeof ctx === "string" ? evaluateExpr(ctx, context) : ctx;
    Object.assign(context, subCtx);
  }
  return context;
}
