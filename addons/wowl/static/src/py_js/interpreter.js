/** @odoo-module **/
import { BUILTINS, PyDate, parseArgs, PyDateTime, PyTime, PyRelativeDelta } from "./builtins";
import { PY_DICT } from "./utils";

// -----------------------------------------------------------------------------
// Types
// -----------------------------------------------------------------------------

/**
 * @typedef { import("./parser").AST } AST
 */

// -----------------------------------------------------------------------------
// Constants and helpers
// -----------------------------------------------------------------------------

const isTrue = BUILTINS.bool;

/**
 * @param {AST} ast
 * @param {Object} context
 * @returns {any}
 */
function applyUnaryOp(ast, context) {
  const expr = evaluate(ast.right, context);
  switch (ast.op) {
    case "-":
      return -expr;
    case "+":
      return expr;
    case "not":
      return !isTrue(expr);
  }
  throw new Error("error");
}

/**
 * We want to maintain this order:
 *   None < number (boolean) < dict < string < list < dict
 * So, each type is mapped to a number to represent that order
 *
 * @param {any} val
 * @returns {number} index type
 */
function pytypeIndex(val) {
  switch (typeof val) {
    case "object":
      // None, List, Object, Dict
      return val === null ? 1 : Array.isArray(val) ? 5 : 3;
    case "number":
      return 2;
    case "string":
      return 4;
  }
  throw new Error("hmmm");
}

/**
 * Compare two values
 *
 * @param {any} left
 * @param {any} right
 * @returns {boolean}
 */
function isLess(left, right) {
  if (typeof left === "number" && typeof right === "number") {
    return left < right;
  }
  if (typeof left === "boolean") {
    left = left ? 1 : 0;
  }
  if (typeof right === "boolean") {
    right = right ? 1 : 0;
  }
  const leftIndex = pytypeIndex(left);
  const rightIndex = pytypeIndex(right);
  if (leftIndex === rightIndex) {
    return left < right;
  }
  return leftIndex < rightIndex;
}

/**
 * @param {any} left
 * @param {any} right
 * @returns {boolean}
 */
function isEqual(left, right) {
  if (typeof left !== typeof right) {
    if (typeof left === "boolean" && typeof right === "number") {
      return right === (left ? 1 : 0);
    }
    if (typeof left === "number" && typeof right === "boolean") {
      return left === (right ? 1 : 0);
    }
    return false;
  }
  return left === right;
}

/**
 * @param {any} left
 * @param {any} right
 * @returns {boolean}
 */
function isIn(left, right) {
  if (Array.isArray(right)) {
    return right.includes(left);
  }
  if (typeof right === "string" && typeof left === "string") {
    return right.includes(left);
  }
  return false;
}

/**
 * @param {AST} ast
 * @param {object} context
 * @returns {any}
 */
function applyBinaryOp(ast, context) {
  const left = evaluate(ast.left, context);
  const right = evaluate(ast.right, context);
  switch (ast.op) {
    case "+":
      const isLeftDelta = left instanceof PyRelativeDelta;
      const isRightDelta = right instanceof PyRelativeDelta;
      if (isLeftDelta || isRightDelta) {
        const date = isLeftDelta ? right : left;
        const delta = isLeftDelta ? left : right;
        return PyRelativeDelta.add(date, delta);
      }
      return left + right;
    case "-":
      return left - right;
    case "*":
      return left * right;
    case "/":
      return left / right;
    case "%":
      return left % right;
    case "//":
      return Math.floor(left / right);
    case "**":
      return left ** right;
    case "==":
      return isEqual(left, right);
    case "<>":
    case "!=":
      return !isEqual(left, right);
    case "<":
      return isLess(left, right);
    case ">":
      return isLess(right, left);
    case ">=":
      return isEqual(left, right) || isLess(right, left);
    case "<=":
      return isEqual(left, right) || isLess(left, right);
    case "in":
      return isIn(left, right);
    case "not in":
      return !isIn(left, right);
  }
  throw new Error("error");
}

const DICT = {
  get(dict) {
    return (...args) => {
      const { key, defValue } = parseArgs(args, ["key", "defValue"]);
      if (key in dict) {
        return dict[key];
      } else if (defValue) {
        return defValue;
      }
      return null;
    };
  },
};

// -----------------------------------------------------------------------------
// Evaluate function
// -----------------------------------------------------------------------------

/**
 * @param {AST} ast
 * @param {Object} context
 * @returns {any}
 */
export function evaluate(ast, context = {}) {
  const dicts = new Set();

  /**
   * @param {AST} ast
   */
  function _evaluate(ast) {
    switch (ast.type) {
      case 0 /* Number */:
      case 1 /* String */:
        return ast.value;
      case 5 /* Name */:
        if (ast.value in context) {
          return context[ast.value];
        } else if (ast.value in BUILTINS) {
          return BUILTINS[ast.value];
        } else {
          throw new Error(`Name '${ast.value}' is not defined`);
        }
      case 3 /* None */:
        return null;
      case 2 /* Boolean */:
        return ast.value;
      case 6 /* UnaryOperator */:
        return applyUnaryOp(ast, context);
      case 7 /* BinaryOperator */:
        return applyBinaryOp(ast, context);
      case 14 /* BooleanOperator */:
        const left = _evaluate(ast.left);
        if (ast.op === "and") {
          return isTrue(left) ? _evaluate(ast.right) : left;
        } else {
          return isTrue(left) ? left : _evaluate(ast.right);
        }
      case 4 /* List */:
      case 10 /* Tuple */:
        return ast.value.map(_evaluate);
      case 11 /* Dictionary */:
        const dict = {};
        for (let key in ast.value) {
          dict[key] = _evaluate(ast.value[key]);
        }
        dicts.add(dict);
        return dict;
      case 8 /* FunctionCall */:
        const fnValue = _evaluate(ast.fn);
        const args = ast.args.map(_evaluate);
        const kwargs = {};
        for (let kwarg in ast.kwargs) {
          kwargs[kwarg] = _evaluate(ast.kwargs[kwarg]);
        }
        if (
          fnValue === PyDate ||
          fnValue === PyDateTime ||
          fnValue === PyTime ||
          fnValue === PyRelativeDelta
        ) {
          return fnValue.create(...args, kwargs);
        }
        return fnValue(...args, kwargs);
      case 12 /* Lookup */: {
        const dict = _evaluate(ast.target);
        const key = _evaluate(ast.key);
        return dict[key];
      }
      case 13 /* If */: {
        if (isTrue(_evaluate(ast.condition))) {
          return _evaluate(ast.ifTrue);
        } else {
          return _evaluate(ast.ifFalse);
        }
      }
      case 15 /* ObjLookup */: {
        const left = _evaluate(ast.obj);
        if (dicts.has(left) || Object.isPrototypeOf.call(PY_DICT, left)) {
          // this is a dictionary => need to apply dict methods
          return DICT[ast.key](left);
        }
        if (left instanceof Date) {
          const result = left[ast.key];
          return typeof result === "function" ? result.bind(left) : result;
        }
        return left[ast.key];
      }
    }
    throw new Error("evaluate error");
  }
  return _evaluate(ast);
}
