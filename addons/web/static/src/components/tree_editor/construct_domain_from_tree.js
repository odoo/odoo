// @ts-check

/** @module @web/components/tree_editor/construct_domain_from_tree - Converts a condition tree into an Odoo domain string representation */

/** @import { AST } from "@web/core/py_js/py_parser" */
/** @import { Tree, Condition, Value } from "./condition_tree" */

import { formatAST, parseExpr } from "@web/core/py_js/py";

import { isBool, isNot } from "./ast_utils";
import {
    astFromValue,
    condition,
    Expression,
    FALSE_TREE,
    isTree,
    TRUE_TREE,
} from "./condition_tree";

/**
 * Wrap an AST node in a `bool()` call unless it is already boolean-like.
 * @param {AST} ast
 * @returns {AST}
 */
function bool(ast) {
    if (isBool(ast) || isNot(ast) || ast.type === 2) {
        return ast;
    }
    return { type: 8, fn: { type: 5, value: "bool" }, args: [ast], kwargs: {} };
}

/**
 * Recursively convert a tree node into an array of AST nodes representing
 * the prefix-notation domain (connectors before their operands).
 * @param {Tree} tree
 * @param {boolean} [isSubTree=false] - whether this tree is nested inside a condition value
 * @returns {AST[]}
 */
function getASTs(tree, isSubTree = false) {
    const ASTs = [];
    if (tree.type === "condition") {
        if (tree.negate) {
            ASTs.push(toAST("!"));
        }
        ASTs.push({
            type: 10,
            value: [tree.path, tree.operator, tree.value].map(toAST),
        });
        return ASTs;
    }

    if (tree.type === "complex_condition") {
        const ast = parseExpr(tree.value);
        return getASTs(condition(new Expression(bool(ast)), "=", 1));
    }

    const length = tree.children.length;
    if (length === 0) {
        if (tree.value === "|") {
            return tree.negate ? getASTs(TRUE_TREE) : getASTs(FALSE_TREE);
        } else {
            return tree.negate
                ? getASTs(FALSE_TREE)
                : isSubTree
                  ? getASTs(TRUE_TREE)
                  : [];
        }
    }

    if (tree.negate) {
        ASTs.push(toAST("!"));
    }
    for (let i = 0; i < length - 1; i++) {
        ASTs.push(toAST(tree.value));
    }
    for (const child of tree.children) {
        ASTs.push(...getASTs(child, true));
    }
    return ASTs;
}

/**
 * Convert a tree or scalar value into its AST representation.
 * Sub-trees become list ASTs (type 4) of their domain encoding.
 * @param {Value|Tree} value
 * @returns {AST}
 */
function toAST(value) {
    if (isTree(value)) {
        return { type: 4, value: getASTs(value) };
    }
    return astFromValue(value);
}

/**
 * Convert a condition tree into a domain string (e.g. `"[('name', '=', 'foo')]"`).
 * @param {Tree} tree
 * @returns {string}
 */
export function constructDomainFromTree(tree) {
    return formatAST(toAST(tree));
}
