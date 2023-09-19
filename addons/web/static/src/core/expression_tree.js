/** @odoo-module **/

import { formatAST, parseExpr } from "@web/core/py_js/py";
import {
    addChild,
    createBetweenOperators,
    Expression,
    removeBetweenOperators,
    TERM_OPERATORS_NEGATION,
    toAST,
    toDomain as domainFromTree,
    toTree as treeFromDomain,
    toValue,
} from "@web/core/domain_tree";

/**
 * @typedef {Object} AtomicExpression
 * @property {"atomic_expression"} type
 * @property {string} value expression
 */

/**
 * @typedef {Object} Options
 * @property {Function} [getFieldDef]
 * @property {boolean} [distributeNot]
 * @property {"&"|"|"} [defaultConnector]
 */

/**
 * @typedef {import("@web/core/domain_tree").Tree|AtomicExpression} ExpressionTree
 */

function not(ast) {
    return { type: 6, op: "not", right: isBool(ast) ? ast.args[0] : ast };
}

function bool(ast) {
    if (isBool(ast)) {
        return ast;
    }
    return { type: 8, fn: { type: 5, value: "bool" }, args: [ast], kwargs: {} };
}

function name(value) {
    return { type: 5, value };
}

function or(left, right) {
    return { type: 14, op: "or", left, right };
}

function and(left, right) {
    return { type: 14, op: "and", left, right };
}

function isNot(ast) {
    return ast.type === 6 && ast.op === "not";
}

function isBool(ast) {
    return (
        ast.type === 8 &&
        ast.fn &&
        ast.fn.type === 5 &&
        ast.fn.value === "bool" &&
        ast.args &&
        ast.args.length === 1
    ); // improve condition?
}

function isValidPath(ast, options) {
    const getFieldDef = options.getFieldDef || (() => null);
    if (ast.type === 5) {
        return getFieldDef(ast.value) !== null;
    }
    // if (ast.type === 15) {
    //     return ast.obj.type === 5 && ast.obj.value === "parent" // && ? ast.key is a name but...
    // }
    return false;
}

const EXCHANGE = {
    "<": ">",
    "<=": ">=",
    ">": "<",
    ">=": "<=",
    "=": "=",
    "!=": "!=",
};

const COMPARATORS = ["<", "<=", ">", ">=", "in", "not in", "==", "is", "!=", "is not"];

/**
 * @param {AST} ast
 * @param {Options} options
 * @param {boolean} [negate=false]
 * @returns {import("@web/core/domain_tree").Condition|AtomicExpression}
 */
function leafFromAST(ast, options, negate = false) {
    if (isValidPath(ast, options)) {
        return {
            type: "condition",
            negate: false,
            path: ast.value,
            operator: negate ? "=" : "!=",
            value: false,
        };
    }

    if (ast.type === 7 && COMPARATORS.includes(ast.op)) {
        const tree = { type: "condition", negate: false };

        let operator = ast.op;
        if (["==", "is"].includes(operator)) {
            operator = "=";
        } else if (operator === "is not") {
            operator = "!=";
        }
        if (negate) {
            operator = TERM_OPERATORS_NEGATION[operator];
        }

        let left = ast.left;
        let right = ast.right;
        const exchange =
            !isValidPath(left, options) && isValidPath(right, options) && EXCHANGE[operator];
        if (exchange) {
            left = ast.right;
            right = ast.left;
            operator = EXCHANGE[operator];
        }
        tree.path = isValidPath(left, options) ? left.value : toValue(left);
        tree.operator = operator;
        tree.value = toValue(right);
        return tree;
    }

    if (
        !negate &&
        ast.type === 16 &&
        ast.iterator &&
        isValidPath(ast.iterator, options) &&
        ast.condition &&
        ast.condition.type === 7 &&
        ["in", "not in"].includes(ast.condition.op)
    ) {
        return {
            type: "condition",
            negate: false,
            path: ast.iterator.value,
            operator: ast.condition.op,
            value: toValue(ast.condition.right),
        };
    }

    if (ast.type === 2) {
        return {
            negate: false,
            type: "condition",
            path: ast.value ? 1 : 0,
            operator: "=",
            value: 1,
        };
    }

    return {
        type: "atomic_expression",
        value: formatAST(negate ? not(ast) : bool(ast)),
    };
}

/**
 * @param {AST} ast
 * @param {Options} options
 * @param {boolean} [negate=false]
 * @returns {Tree}
 */
function expressionTreeFromAST(ast, options, negate = false) {
    if (isNot(ast)) {
        return expressionTreeFromAST(ast.right, options, !negate);
    }

    if (ast.type === 14) {
        const tree = {
            type: "connector",
            value: ast.op === "and" ? "&" : "|", // and/or are the only ops that are given type 14 (for now)
            children: [],
        };
        if (options.distributeNot && negate) {
            tree.value = tree.value === "&" ? "|" : "&";
            tree.negate = false;
        } else {
            tree.negate = negate;
        }
        const subASTs = [ast.left, ast.right];
        for (const subAST of subASTs) {
            const child = expressionTreeFromAST(subAST, options, options.distributeNot && negate);
            addChild(tree, child);
        }
        return tree;
    }

    if (ast.type === 13) {
        const newAST = or(and(ast.condition, ast.ifTrue), and(not(ast.condition), ast.ifFalse));
        return expressionTreeFromAST(newAST, options, negate);
    }

    return leafFromAST(ast, options, negate);
}

function _expressionFromExpressionTree(tree, options, isRoot = false) {
    if (tree.type === "connector") {
        const connector = tree.value === "&" ? "and" : "or";
        const subExpressions = tree.children.map((c) => _expressionFromExpressionTree(c, options));
        let expression = subExpressions.join(` ${connector} `);
        if (!isRoot || tree.negate) {
            expression = `( ${expression} )`;
        }
        if (tree.negate) {
            expression = `not ${expression}`;
        }
        return expression;
    }

    if (tree.type === "atomic_expression") {
        return tree.value;
    }

    const { path } = tree;
    const pathAST = toAST(path);

    if (typeof path === "number") {
        if ([0, 1].includes(path)) {
            // we should check if we have (0/1, "="", 1)
            return formatAST({ type: 2, value: Boolean(path) });
        } else {
            throw new Error("Bloop");
        }
    }

    if (isBool(pathAST) || isNot(pathAST)) {
        // path must be an Expression instance
        // check operator and value? might not be necessary if expression editor locks operator and value
        return formatAST(pathAST);
    }

    if (typeof path === "string" && isValidPath(name(path), options)) {
        // fieldDefs instead of getFieldDef?
        // check negate, everything in face :-)
        let operator = tree.operator;
        if (typeof operator === "string") {
            if (operator === "=") {
                operator = "=="; // or is?
            }
            if (!COMPARATORS.includes(operator)) {
                throw new Error("Bloop");
            }
            // check if operator is valid
        } else {
            throw new Error("Bloop");
        }
        if (operator === "==" && tree.value === false) {
            return `not ${path}`;
        }
        if (operator === "!=" && tree.value === false) {
            return `${path}`;
        }

        return `${path} ${operator} ${formatAST(toAST(tree.value))}`;
    }

    return formatAST(bool(pathAST)); // not good of course
}

/**
 * PUBLIC
 */

/**
 * @param {import("@web/core/domain_tree").Tree} tree
 * @returns {ExpressionTree}
 */
export function expressionTreeFromTree(tree) {
    if (tree.type === "condition") {
        if (tree.path instanceof Expression && tree.operator === "=" && tree.value === 1) {
            return {
                type: "atomic_expression",
                value: String(tree.path),
            };
        }
        return { ...tree };
    }
    return {
        ...tree,
        children: tree.children.map((child) => expressionTreeFromTree(child)),
    };
}

/**
 * @param {ExpressionTree} expressionTree
 * @returns {import("@web/core/domain_tree").Tree}
 */
export function treeFromExpressionTree(expressionTree) {
    if (expressionTree.type === "condition") {
        return { ...expressionTree };
    }
    if (expressionTree.type === "atomic_expression") {
        return {
            type: "condition",
            path: new Expression(parseExpr(expressionTree.value)), // instance of expression by construction
            operator: "=",
            value: 1,
        };
    }
    return {
        ...expressionTree,
        children: expressionTree.children.map((child) => treeFromExpressionTree(child)),
    };
}

/**
 * @param {string} expression
 * @param {Options} [options={}]
 * @returns {ExpressionTree} a tree representation of an expression
 */
export function expressionTreeFromExpression(expression, options = {}) {
    const ast = parseExpr(expression);

    const expressionTree = expressionTreeFromAST(ast, options);
    const tree = treeFromExpressionTree(expressionTree);
    const simplifiedTree = createBetweenOperators(tree); // modify createBetweenOperators to accept atomic_condition?
    const newExressionTree = expressionTreeFromTree(simplifiedTree);

    if (newExressionTree.type === "connector") {
        return newExressionTree;
    }

    const value = options.defaultConnector || "&";
    return { type: "connector", value, negate: false, children: [newExressionTree] };
}

/**
 * @param {ExpressionTree} expressionTree
 * @param {Options} [options={}]
 * @returns {string} an expression
 */
export function expressionFromExpressionTree(expressionTree, options = {}) {
    const tree = treeFromExpressionTree(expressionTree);
    const simplifiedTree = removeBetweenOperators(tree); // modify createBetweenOperators to accept atomic_condition?
    const newExressionTree = expressionTreeFromTree(simplifiedTree);
    return _expressionFromExpressionTree(newExressionTree, options, true);
}

/**
 * @param {string} domain a string representation of a domain
 * @param {Options} [options={}]
 * @returns {string} an expression
 */
export function expressionFromDomain(domain, options = {}) {
    const tree = treeFromDomain(domain, options);
    const expressionTree = expressionTreeFromTree(tree);
    return expressionFromExpressionTree(expressionTree, options);
}

/**
 * @param {string} expression an expression
 * @param {Options} [options={}]
 * @returns {string} a string representation of a domain
 */
export function domainFromExpression(expression, options = {}) {
    const expressionTree = expressionTreeFromExpression(expression, options);
    const tree = treeFromExpressionTree(expressionTree);
    return domainFromTree(tree);
}
