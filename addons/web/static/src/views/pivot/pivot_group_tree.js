// @ts-check

/** @module @web/views/pivot/pivot_group_tree - Tree data structure for managing pivot table row/column group hierarchies */

import { sortBy } from "@web/core/utils/collections/arrays";
/**
 * Add labels/values in the provided groupTree. A new leaf is created in
 * the groupTree with a root object corresponding to the group with given
 * labels/values.
 *
 * @param {Object} groupTree
 * @param {string[]} labels
 * @param {Array} values
 */
export function addGroup(groupTree, labels, values) {
    let tree = groupTree;
    for (const value of values.slice(0, -1)) {
        tree = tree.directSubTrees.get(value);
    }
    const value = values.at(-1);
    if (tree.directSubTrees.has(value)) {
        return;
    }
    tree.directSubTrees.set(value, {
        root: { labels, values },
        directSubTrees: new Map(),
    });
}

/**
 * Find a group with given values in the provided groupTree.
 *
 * @param {Object} groupTree
 * @param {Array} values
 * @returns {Object}
 */
export function findGroup(groupTree, values) {
    let tree = groupTree;
    for (const value of values) {
        tree = tree.directSubTrees.get(value);
        if (!tree) {
            return undefined;
        }
    }
    return tree;
}

/**
 * Make any group in tree a leaf if it was a leaf in oldTree.
 *
 * @param {Object} tree
 * @param {Object} oldTree
 */
export function pruneTree(tree, oldTree) {
    if (!oldTree.directSubTrees.size) {
        tree.directSubTrees.clear();
        delete tree.sortedKeys;
        return;
    }
    for (const subTreeKey of [...tree.directSubTrees.keys()]) {
        const subTree = tree.directSubTrees.get(subTreeKey);
        if (!oldTree.directSubTrees.has(subTreeKey)) {
            subTree.directSubTrees.clear();
            delete subTree.sortedKeys;
        } else {
            pruneTree(subTree, oldTree.directSubTrees.get(subTreeKey));
        }
    }
}

/**
 * Sort recursively the subTrees of tree using sortFunction.
 *
 * @param {Function} sortFunction
 * @param {Object} tree
 */
export function sortTree(sortFunction, tree) {
    tree.sortedKeys = sortBy([...tree.directSubTrees.keys()], sortFunction(tree));
    for (const subTree of tree.directSubTrees.values()) {
        sortTree(sortFunction, subTree);
    }
}

/**
 * Returns the height of a given groupTree.
 *
 * @param {Object} tree
 * @returns {number}
 */
export function getTreeHeight(tree) {
    const subTreeHeights = [...tree.directSubTrees.values()].map(getTreeHeight);
    return Math.max(0, ...subTreeHeights) + 1;
}

/**
 * Returns the leaf counts of each group inside the given tree.
 *
 * @param {Object} tree
 * @returns {Object} keys are group ids
 */
export function getLeafCounts(tree) {
    const leafCounts = {};
    let leafCount;
    if (!tree.directSubTrees.size) {
        leafCount = 1;
    } else {
        leafCount = [...tree.directSubTrees.values()].reduce((acc, subTree) => {
            const subLeafCounts = getLeafCounts(subTree);
            Object.assign(leafCounts, subLeafCounts);
            return acc + leafCounts[JSON.stringify(subTree.root.values)];
        }, 0);
    }
    leafCounts[JSON.stringify(tree.root.values)] = leafCount;
    return leafCounts;
}

/**
 * @param {Object} data
 * @returns {boolean} true iff there's data in the table
 */
export function hasData(data) {
    const key = JSON.stringify([[], []]);
    return data.counts[key] > 0;
}
