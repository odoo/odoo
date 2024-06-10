import { DIRECTIONS } from "./position";

export const closestPath = function* (node) {
    while (node) {
        yield node;
        node = node.parentNode;
    }
};

/**
 * Find a node.
 * @param {findCallback} findCallback - This callback check if this function
 *      should return `node`.
 * @param {findCallback} stopCallback - This callback check if this function
 *      should stop when it receive `node`.
 */
export function findNode(domPath, findCallback = () => true, stopCallback = () => false) {
    for (const node of domPath) {
        if (findCallback(node)) {
            return node;
        }
        if (stopCallback(node)) {
            break;
        }
    }
    return null;
}

/**
 * Returns the closest HTMLElement of the provided Node. If the predicate is a
 * string, returns the closest HTMLElement that match the predicate selector. If
 * the predicate is a function, returns the closest element that matches the
 * predicate. Any returned element will be contained within the editable.
 *
 * @param {Node} node
 * @param {string | Function} [predicate='*']
 * @returns {HTMLElement|null}
 */
export function closestElement(node, predicate = "*") {
    let element = node.nodeType === Node.ELEMENT_NODE ? node : node.parentElement;
    if (typeof predicate === "function") {
        while (element && !predicate(element)) {
            element = element.parentElement;
        }
    } else {
        element = element?.closest(predicate);
    }

    return element?.closest(".odoo-editor-editable") && element;
}

/**
 * Returns a list of all the ancestors nodes of the provided node.
 *
 * @param {Node} node
 * @param {Node} [editable] include to prevent bubbling up further than the editable.
 * @returns {HTMLElement[]}
 */
export function ancestors(node, editable) {
    if (!node || !node.parentElement || node === editable) {
        return [];
    }
    return [node.parentElement, ...ancestors(node.parentElement, editable)];
}

/**
 * Take a node, return all of its descendants, in depth-first order.
 *
 * @param {Node} node
 * @returns {Node[]}
 */
export function descendants(node) {
    const posterity = [];
    for (const child of node.childNodes || []) {
        posterity.push(child, ...descendants(child));
    }
    return posterity;
}

/**
 * Values which can be returned while browsing the DOM which gives information
 * to why the path ended.
 */
export const PATH_END_REASONS = {
    NO_NODE: 0,
    BLOCK_OUT: 1,
    BLOCK_HIT: 2,
    OUT_OF_SCOPE: 3,
};

/**
 * Creates a generator function according to the given parameters. Pre-made
 * generators to traverse the DOM are made using this function:
 *
 * @see leftLeafFirstPath
 * @see leftLeafOnlyNotBlockPath
 * @see leftLeafOnlyInScopeNotBlockEditablePath
 * @see rightLeafOnlyNotBlockPath
 * @see rightLeafOnlyNotBlockNotEditablePath
 *
 * @param {boolean} direction
 * @param {Object} options
 * @param {boolean} [options.leafOnly] if true, do not yield any non-leaf node
 * @param {boolean} [options.inScope] if true, stop the generator as soon as a node is not
 *                      a descendant of `node` provided when traversing the
 *                      generated function.
 * @param {Function} [options.stopTraverseFunction] a function that takes a node
 *                      and should return true when a node descendant should not
 *                      be traversed.
 * @param {Function} [options.stopFunction] function that makes the generator stop when a
 *                      node is encountered.
 */
export function createDOMPathGenerator(
    direction,
    { leafOnly = false, inScope = false, stopTraverseFunction, stopFunction } = {}
) {
    const nextDeepest =
        direction === DIRECTIONS.LEFT
            ? (node) => lastLeaf(node.previousSibling, stopTraverseFunction)
            : (node) => firstLeaf(node.nextSibling, stopTraverseFunction);

    const firstNode =
        direction === DIRECTIONS.LEFT
            ? (node, offset) => lastLeaf(node.childNodes[offset - 1], stopTraverseFunction)
            : (node, offset) => firstLeaf(node.childNodes[offset], stopTraverseFunction);

    // Note "reasons" is a way for the caller to be able to know why the
    // generator ended yielding values.
    return function* (node, offset, reasons = []) {
        let movedUp = false;

        let currentNode = firstNode(node, offset);
        if (!currentNode) {
            movedUp = true;
            currentNode = node;
        }

        while (currentNode) {
            if (stopFunction && stopFunction(currentNode)) {
                reasons.push(movedUp ? PATH_END_REASONS.BLOCK_OUT : PATH_END_REASONS.BLOCK_HIT);
                break;
            }
            if (inScope && currentNode === node) {
                reasons.push(PATH_END_REASONS.OUT_OF_SCOPE);
                break;
            }
            if (!(leafOnly && movedUp)) {
                yield currentNode;
            }

            movedUp = false;
            let nextNode = nextDeepest(currentNode);
            if (!nextNode) {
                movedUp = true;
                nextNode = currentNode.parentNode;
            }
            currentNode = nextNode;
        }

        reasons.push(PATH_END_REASONS.NO_NODE);
    };
}

/**
 * Returns the deepest child in last position.
 *
 * @param {Node} node
 * @param {Function} [stopTraverseFunction]
 * @returns {Node}
 */
export function lastLeaf(node, stopTraverseFunction) {
    while (node && node.lastChild && !(stopTraverseFunction && stopTraverseFunction(node))) {
        node = node.lastChild;
    }
    return node;
}
/**
 * Returns the deepest child in first position.
 *
 * @param {Node} node
 * @param {Function} [stopTraverseFunction]
 * @returns {Node}
 */
export function firstLeaf(node, stopTraverseFunction) {
    while (node && node.firstChild && !(stopTraverseFunction && stopTraverseFunction(node))) {
        node = node.firstChild;
    }
    return node;
}

/**
 * Returns all the previous siblings of the given node until the first
 * sibling that does not satisfy the predicate, in lookup order.
 *
 * @param {Node} node
 * @param {Function} [predicate] (node: Node) => boolean
 */
export function getAdjacentPreviousSiblings(node, predicate = (n) => !!n) {
    let previous = node.previousSibling;
    const list = [];
    while (previous && predicate(previous)) {
        list.push(previous);
        previous = previous.previousSibling;
    }
    return list;
}
/**
 * Returns all the next siblings of the given node until the first
 * sibling that does not satisfy the predicate, in lookup order.
 *
 * @param {Node} node
 * @param {Function} [predicate] (node: Node) => boolean
 */
export function getAdjacentNextSiblings(node, predicate = (n) => !!n) {
    let next = node.nextSibling;
    const list = [];
    while (next && predicate(next)) {
        list.push(next);
        next = next.nextSibling;
    }
    return list;
}
/**
 * Returns all the adjacent siblings of the given node until the first sibling
 * (in both directions) that does not satisfy the predicate, in index order. If
 * the given node does not satisfy the predicate, an empty array is returned.
 *
 * @param {Node} node
 * @param {Function} [predicate] (node: Node) => boolean
 */
export function getAdjacents(node, predicate = (n) => !!n) {
    const previous = getAdjacentPreviousSiblings(node, predicate);
    const next = getAdjacentNextSiblings(node, predicate);
    return predicate(node) ? [...previous.reverse(), node, ...next] : [];
}
/**
 * Return the furthest uneditable parent of node contained within parentLimit.
 * @see deleteRange Used to guarantee that uneditables are fully contained in
 * the range (so that it is not possible to partially remove them)
 *
 * @param {Node} node
 * @param {Node} [parentLimit=undefined] non-inclusive furthest parent allowed
 * @returns {Node} uneditable parent if it exists
 */
export function getFurthestUneditableParent(node, parentLimit) {
    if (node === parentLimit || (parentLimit && !parentLimit.contains(node))) {
        return undefined;
    }
    let parent = node && node.parentElement;
    let nonEditableElement;
    while (parent && (!parentLimit || parent !== parentLimit)) {
        if (!parent.isContentEditable) {
            nonEditableElement = parent;
        }
        if (parent.classList.contains("odoo-editor-editable")) {
            break;
        }
        parent = parent.parentElement;
    }
    return nonEditableElement;
}

/**
 * Returns the deepest common ancestor element of the given nodes within the
 * specified root element. If no root element is provided, the entire document
 * is considered as the root.
 *
 * @param {Node[]} nodes - The nodes for which to find the common ancestor.
 * @param {Element} [root] - The root element within which to search for the common ancestor.
 * @returns {Element|null} - The common ancestor element, or null if no common ancestor is found.
 */
export function getCommonAncestor(nodes, root = undefined) {
    const pathsToRoot = nodes.map((node) => [node, ...ancestors(node, root)]);

    let candidate = pathsToRoot[0]?.at(-1);
    if (root && candidate !== root) {
        return null;
    }
    let commonAncestor = null;
    while (candidate && pathsToRoot.every((path) => path.at(-1) === candidate)) {
        commonAncestor = candidate;
        pathsToRoot.forEach((path) => path.pop());
        candidate = pathsToRoot[0].at(-1);
    }
    return commonAncestor;
}
