// @ts-check

/** @module @web/components/tree_editor/tree_from_expression - High-level expression-to-tree conversion with virtual operator introduction */

/** @import { Tree, Options } from "./condition_tree" */

import { constructTreeFromExpression } from "./construct_tree_from_expression";
import { introduceVirtualOperators } from "./virtual_operators";

/**
 * Parse a Python expression into a condition tree with virtual operators.
 * @param {string} expression
 * @param {Options} [options]
 * @returns {Tree}
 */
export function treeFromExpression(expression, options = {}) {
    const tree = constructTreeFromExpression(expression, options);
    return introduceVirtualOperators(tree, options);
}
