/** @odoo-module **/
import { tokenize } from "./tokenizer";
import { parse } from "./parser";
import { evaluate } from "./interpreter";
export { tokenize } from "./tokenizer";
export { parse } from "./parser";
export { evaluate } from "./interpreter";
export { formatAST } from "./utils";
export function parseExpr(expr) {
  const tokens = tokenize(expr);
  return parse(tokens);
}
export function evaluateExpr(expr, context) {
  const ast = parseExpr(expr);
  return evaluate(ast, context);
}
