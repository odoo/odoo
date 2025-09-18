// @ts-check

/** @module @web/components/tree_editor/domain_contains_expressions - Checks whether a domain string contains dynamic Python expressions */

/** @import { Tree } from "./condition_tree" */
/** @import { DomainRepr } from "@web/core/domain" */

import { Expression, isTree } from "./condition_tree";
import { constructTreeFromDomain } from "./construct_tree_from_domain";

/**
 * Recursively check whether any node in the tree contains an Expression value.
 * @param {Tree} tree
 * @returns {boolean}
 */
function treeContainsExpressions(tree) {
    if (tree.type === "condition") {
        const { path, operator, value } = tree;
        if (isTree(value) && treeContainsExpressions(value)) {
            return true;
        }
        return [path, operator, value].some(
            (v) =>
                v instanceof Expression ||
                (Array.isArray(v) && v.some((w) => w instanceof Expression)),
        );
    }
    for (const child of tree.children) {
        if (treeContainsExpressions(child)) {
            return true;
        }
    }
    return false;
}

/**
 * Check whether a domain contains dynamic Python expressions.
 * @param {DomainRepr} domain
 * @returns {boolean|null} true/false if parseable, null if domain is invalid
 */
export function domainContainsExpressions(domain) {
    let tree;
    try {
        tree = constructTreeFromDomain(domain);
    } catch {
        return null;
    }
    // detect expressions in the domain tree, which we know is well-formed
    return treeContainsExpressions(tree);
}
