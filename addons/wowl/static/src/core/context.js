/** @odoo-module **/
import { evaluateExpr } from "../py/index";
export function makeContext(...contexts) {
  let context = {};
  for (let ctx of contexts) {
    const subCtx = typeof ctx === "string" ? evaluateExpr(ctx, context) : ctx;
    Object.assign(context, subCtx);
  }
  return context;
}
