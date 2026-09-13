// @ts-check
/** @odoo-module native */

import { sortBy } from "@web/core/utils/collections/arrays";
/**
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
 * @param {Record<string, any>} groupTree
 * @param {any[]} values
 * @returns {Record<string, any> | undefined}
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
 * @param {Object} tree
 * @param {Object} oldTree
 */
export function removeMissingSubTrees(tree, oldTree) {
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
            removeMissingSubTrees(subTree, oldTree.directSubTrees.get(subTreeKey));
        }
    }
}

/**
 * @param {Function} sortFunction
 * @param {Object} tree
 */
export function sortTree(sortFunction, tree) {
    tree.sortedKeys = sortBy([...tree.directSubTrees.keys()], sortFunction(tree));
    for (const subTree of tree.directSubTrees.values()) {
        sortTree(sortFunction, subTree);
    }
}

/** @param {Object} tree */
export function stripSortedKeys(tree) {
    delete tree.sortedKeys;
    for (const subTree of tree.directSubTrees.values()) {
        stripSortedKeys(subTree);
    }
}

/**
 * @param {Object} tree
 * @returns {number}
 */
export function getTreeHeight(tree) {
    let height = 0;
    for (const subTree of tree.directSubTrees.values()) {
        height = Math.max(height, getTreeHeight(subTree));
    }
    return height + 1;
}

/**
 * @param {Object} tree
 * @returns {Object}
 */
export function getLeafCounts(tree, leafCounts = {}) {
    let leafCount = 0;
    if (!tree.directSubTrees.size) {
        leafCount = 1;
    } else {
        for (const subTree of tree.directSubTrees.values()) {
            getLeafCounts(subTree, leafCounts);
            leafCount += leafCounts[JSON.stringify(subTree.root.values)];
        }
    }
    leafCounts[JSON.stringify(tree.root.values)] = leafCount;
    return leafCounts;
}

/**
 * @param {Object} data
 * @returns {boolean}
 */
export function hasData(data) {
    const key = JSON.stringify([[], []]);
    return data.counts[key] > 0;
}
