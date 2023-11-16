/** @odoo-module **/

import { BUILTINS, execOnIterable } from "./py_builtin";
import { PyDate, PyDateTime, PyRelativeDelta, PyTime, PyTimeDelta } from "./py_date";
import { PY_DICT, toPyDict } from "./py_utils";
import { parseArgs } from "./py_parser";
import { error, isError, map, mapObject, throwError } from "@web/core/error";

// -----------------------------------------------------------------------------
// Types
// -----------------------------------------------------------------------------

/**
 * @typedef { import("./py_parser").AST } AST
 */

/**
 * @typedef {import("@web/core/error").Err} Err
 */

// -----------------------------------------------------------------------------
// Constants and helpers
// -----------------------------------------------------------------------------

const isTrue = BUILTINS.bool;

/**
 * @param {string} op
 * @param {any} right
 * @returns {any|Err}
 */
function tryApplyUnaryOp(op, right) {
    switch (op) {
        case "-":
            if (right instanceof Object && right.negate) {
                return right.negate();
            }
            return -right;
        case "+":
            return right;
        case "not":
            return !isTrue(right);
    }
    return error(`Unknown unary operator: ${op}`);
}

/**
 * We want to maintain this order:
 *   None < number (boolean) < dict < string < list < dict
 * So, each type is mapped to a number to represent that order
 *
 * @param {any} val
 * @returns {number|Err} index type
 */
function tryPytypeIndex(val) {
    switch (typeof val) {
        case "object":
            // None, List, Object, Dict
            return val === null ? 1 : Array.isArray(val) ? 5 : 3;
        case "number":
            return 2;
        case "string":
            return 4;
    }
    return error(`Unknown type: ${typeof val}`);
}

/**
 * @param {Object} obj
 * @returns {boolean}
 */
function isConstructor(obj) {
    return !!obj.prototype && !!obj.prototype.constructor.name;
}

/**
 * Compare two values
 *
 * @param {any} left
 * @param {any} right
 * @returns {boolean|Err}
 */
function tryIsLess(left, right) {
    if (typeof left === "number" && typeof right === "number") {
        return left < right;
    }
    if (typeof left === "boolean") {
        left = left ? 1 : 0;
    }
    if (typeof right === "boolean") {
        right = right ? 1 : 0;
    }
    const result = map(tryPytypeIndex)([left, right]);
    if (isError(result)) {
        return result;
    }
    const [leftIndex, rightIndex] = result;
    if (leftIndex === rightIndex) {
        return left < right;
    }
    return leftIndex < rightIndex;
}

/**
 * @param {any} left
 * @param {any} right
 * @returns {boolean|Err}
 */
function tryIsEqual(left, right) {
    if (typeof left !== typeof right) {
        if (typeof left === "boolean" && typeof right === "number") {
            return right === (left ? 1 : 0);
        }
        if (typeof left === "number" && typeof right === "boolean") {
            return left === (right ? 1 : 0);
        }
        return false;
    }
    if (left instanceof Object && left.isEqual) {
        return left.isEqual(right);
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
    if (typeof right === "object") {
        return left in right;
    }
    return false;
}

/**
 * @param {string} op
 * @param {any} left
 * @param {any} right
 * @returns {any|Err}
 */
function tryApplyBinaryOp(op, left, right) {
    switch (op) {
        case "+": {
            const relativeDeltaOnLeft = left instanceof PyRelativeDelta;
            const relativeDeltaOnRight = right instanceof PyRelativeDelta;
            if (relativeDeltaOnLeft || relativeDeltaOnRight) {
                const date = relativeDeltaOnLeft ? right : left;
                const delta = relativeDeltaOnLeft ? left : right;
                return PyRelativeDelta.add(date, delta);
            }

            const timeDeltaOnLeft = left instanceof PyTimeDelta;
            const timeDeltaOnRight = right instanceof PyTimeDelta;
            if (timeDeltaOnLeft && timeDeltaOnRight) {
                return left.add(right);
            }
            if (timeDeltaOnLeft) {
                if (right instanceof PyDate || right instanceof PyDateTime) {
                    return right.add(left);
                } else {
                    return error("Not supported");
                }
            }
            if (timeDeltaOnRight) {
                if (left instanceof PyDate || left instanceof PyDateTime) {
                    return left.add(right);
                } else {
                    return error("Not supported");
                }
            }
            if (left instanceof Array && right instanceof Array) {
                return [...left, ...right];
            }

            return left + right;
        }
        case "-": {
            const isRightDelta = right instanceof PyRelativeDelta;
            if (isRightDelta) {
                return PyRelativeDelta.substract(left, right);
            }

            const timeDeltaOnRight = right instanceof PyTimeDelta;
            if (timeDeltaOnRight) {
                if (left instanceof PyTimeDelta) {
                    return left.substract(right);
                } else if (left instanceof PyDate || left instanceof PyDateTime) {
                    return left.substract(right);
                } else {
                    return error("Not supported");
                }
            }

            if (left instanceof PyDate) {
                return left.substract(right);
            }
            return left - right;
        }
        case "*": {
            const timeDeltaOnLeft = left instanceof PyTimeDelta;
            const timeDeltaOnRight = right instanceof PyTimeDelta;
            if (timeDeltaOnLeft || timeDeltaOnRight) {
                const number = timeDeltaOnLeft ? right : left;
                const delta = timeDeltaOnLeft ? left : right;
                return delta.multiply(number); // check number type?
            }

            return left * right;
        }
        case "/":
            return left / right;
        case "%":
            return left % right;
        case "//":
            if (left instanceof PyTimeDelta) {
                return left.divide(right); // check number type?
            }
            return Math.floor(left / right);
        case "**":
            return left ** right;
        case "==":
            return tryIsEqual(left, right);
        case "<>":
        case "!=":
            return !tryIsEqual(left, right);
        case "<":
            return tryIsLess(left, right);
        case ">":
            return tryIsLess(right, left);
        case ">=":
            return tryIsEqual(left, right) || tryIsLess(right, left);
        case "<=":
            return tryIsEqual(left, right) || tryIsLess(left, right);
        case "in":
            return isIn(left, right);
        case "not in":
            return !isIn(left, right);
    }
    return error(`Unknown binary operator: ${op}`);
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

const STRING = {
    lower(str) {
        return () => str.toLowerCase();
    },
    upper(str) {
        return () => str.toUpperCase();
    },
};

function getModifiedFunc(key, func, set) {
    return (...args) => {
        // we always receive at least one argument: kwargs (return fnValue(...args, kwargs); in FunctionCall case)
        if (args.length === 1) {
            return new Set(set);
        }
        if (args.length > 2) {
            return error(`${key}: py_js supports at most 1 argument, got (${args.length - 1})`);
        }
        return execOnIterable(args[0], func);
    };
}

const SET = {
    intersection(set) {
        return getModifiedFunc(
            "intersection",
            (iterable) => {
                const intersection = new Set();
                for (const i of iterable) {
                    if (set.has(i)) {
                        intersection.add(i);
                    }
                }
                return intersection;
            },
            set
        );
    },
    difference(set) {
        return getModifiedFunc(
            "difference",
            (iterable) => {
                iterable = new Set(iterable);
                const difference = new Set();
                for (const e of set) {
                    if (!iterable.has(e)) {
                        difference.add(e);
                    }
                }
                return difference;
            },
            set
        );
    },
    union(set) {
        return getModifiedFunc(
            "union",
            (iterable) => {
                return new Set([...set, ...iterable]);
            },
            set
        );
    },
};

// -----------------------------------------------------------------------------
// Evaluate function
// -----------------------------------------------------------------------------

/**
 * @param {AST} ast
 * @param {Object} context
 * @returns {any|Err}
 */
export function tryEvaluate(ast, context = {}) {
    const dicts = new Set();
    let pyContext;
    const evalContext = Object.create(context);
    if (!evalContext.context) {
        Object.defineProperty(evalContext, "context", {
            get() {
                if (!pyContext) {
                    pyContext = toPyDict(context);
                }
                return pyContext;
            },
        });
    }

    const evaluateSubASTs = mapObject((value) => {
        if (typeof value !== "object" || value === null) {
            return value;
        }
        if (Array.isArray(value)) {
            /** array of ASTs */
            return map(_tryEvaluate)(value);
        }
        /** AST */
        return _tryEvaluate(value);
    });

    /**
     * @param {AST} ast
     * @returns {any|Err}
     */
    function _tryEvaluate(ast) {
        switch (ast.type) {
            case 0 /* Number */:
            case 1 /* String */:
            case 2 /* Boolean */:
                return ast.value;
            case 3 /* None */:
                return null;
            case 5 /* Name */:
                if (ast.value in evalContext) {
                    return evalContext[ast.value];
                } else if (ast.value in BUILTINS) {
                    return BUILTINS[ast.value];
                } else {
                    return error(`Name '${ast.value}' is not defined`);
                }
            case 6 /* UnaryOperator */: {
                const result = evaluateSubASTs(ast);
                if (isError(result)) {
                    return result;
                }
                const { op, right } = result;
                return tryApplyUnaryOp(op, right);
            }
            case 7 /* BinaryOperator */: {
                const result = evaluateSubASTs(ast);
                if (isError(result)) {
                    return result;
                }
                const { op, left, right } = result;
                return tryApplyBinaryOp(op, left, right);
            }
            case 14 /* BooleanOperator */: {
                const left = _tryEvaluate(ast.left);
                if (isError(left)) {
                    return left;
                }
                if (ast.op === "and") {
                    return isTrue(left) ? _tryEvaluate(ast.right) : left;
                } else {
                    return isTrue(left) ? left : _tryEvaluate(ast.right);
                }
            }
            case 4 /* List */:
            case 10 /* Tuple */: {
                return map(_tryEvaluate)(ast.value);
            }
            case 11 /* Dictionary */: {
                return mapObject(_tryEvaluate)(ast.value);
            }
            case 8 /* FunctionCall */: {
                const result = evaluateSubASTs({
                    ...ast,
                    kwargs: null /** avoid confusion ast/object */,
                });
                if (isError(result)) {
                    return result;
                }
                const kwargs = mapObject(_tryEvaluate)(ast.kwargs);
                if (isError(result)) {
                    return kwargs;
                }
                const { fn: fnValue, args } = result;
                if (
                    fnValue === PyDate ||
                    fnValue === PyDateTime ||
                    fnValue === PyTime ||
                    fnValue === PyRelativeDelta ||
                    fnValue === PyTimeDelta
                ) {
                    return fnValue.create(...args, kwargs);
                }
                return fnValue(...args, kwargs);
            }
            case 12 /* Lookup */: {
                const result = evaluateSubASTs(ast);
                if (isError(result)) {
                    return result;
                }
                const { target: dict, key } = result;
                if (dict === null || !["object", "function"].includes(typeof dict)) {
                    return error("Cannot read property");
                }
                return dict[key];
            }
            case 13 /* If */: {
                const cond = _tryEvaluate(ast.condition);
                if (isError(cond)) {
                    return cond;
                }
                if (isTrue(cond)) {
                    return _tryEvaluate(ast.ifTrue);
                } else {
                    return _tryEvaluate(ast.ifFalse);
                }
            }
            case 15 /* ObjLookup */: {
                const left = _tryEvaluate(ast.obj);
                if (isError(left)) {
                    return left;
                }
                if (dicts.has(left) || Object.isPrototypeOf.call(PY_DICT, left)) {
                    // this is a dictionary => need to apply dict methods
                    return DICT[ast.key](left);
                }
                if (typeof left === "string") {
                    return STRING[ast.key](left);
                }
                if (left instanceof Set) {
                    return SET[ast.key](left);
                }
                if (ast.key == "get" && typeof left === "object") {
                    return DICT[ast.key](toPyDict(left));
                }
                if (left === null || !["object", "function"].includes(typeof left)) {
                    return error("Cannot read property");
                }
                const result = left[ast.key];
                if (typeof result === "function" && !isConstructor(result)) {
                    return result.bind(left);
                }
                return result;
            }
        }
        return error(`AST of type ${ast.type} cannot be evaluated`);
    }
    return _tryEvaluate(ast);
}

/**
 * @param {AST} ast
 * @param {Object} context
 * @returns {any}
 */
export function evaluate(ast, context = {}) {
    const result = tryEvaluate(ast, context);
    if (isError(result)) {
        throwError(result);
    }
    return result;
}
