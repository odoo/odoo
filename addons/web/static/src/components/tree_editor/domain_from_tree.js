// @ts-check

/** @module @web/components/tree_editor/domain_from_tree - High-level tree-to-domain conversion with virtual operator elimination */

/** @import { Tree } from "./condition_tree" */

import { constructDomainFromTree } from "./construct_domain_from_tree";
import { eliminateVirtualOperators } from "./virtual_operators";

/**
 * Convert a condition tree to an Odoo domain string.
 * @param {Tree} tree
 * @returns {string}
 */
export function domainFromTree(tree) {
    const simplifiedTree = eliminateVirtualOperators(tree);
    return constructDomainFromTree(simplifiedTree);
}
