// Position and sizes
//------------------------------------------------------------------------------

export const DIRECTIONS = {
    LEFT: false,
    RIGHT: true,
};

/**
 * @param {Node} node
 * @returns {[HTMLElement, number]}
 */
export function leftPos(node) {
    return [node.parentElement, childNodeIndex(node)];
}
/**
 * @param {Node} node
 * @returns {[HTMLElement, number]}
 */
export function rightPos(node) {
    return [node.parentElement, childNodeIndex(node) + 1];
}
/**
 * @param {Node} node
 * @returns {[HTMLElement, number, HTMLElement, number]}
 */
export function boundariesOut(node) {
    const index = childNodeIndex(node);
    return [node.parentElement, index, node.parentElement, index + 1];
}
/**
 * @param {Node} node
 * @returns {[HTMLElement, number, HTMLElement, number]}
 */
export function boundariesIn(node) {
    return [node, 0, node, nodeSize(node)];
}
/**
 * @param {Node} node
 * @returns {[Node, number]}
 */
export function startPos(node) {
    return [node, 0];
}
/**
 * @param {Node} node
 * @returns {[Node, number]}
 */
export function endPos(node) {
    return [node, nodeSize(node)];
}
/**
 * Returns the given node's position relative to its parent (= its index in the
 * child nodes of its parent).
 *
 * @param {Node} node
 * @returns {number}
 */
export function childNodeIndex(node) {
    let i = 0;
    while (node.previousSibling) {
        i++;
        node = node.previousSibling;
    }
    return i;
}
/**
 * Returns the size of the node = the number of characters for text nodes and
 * the number of child nodes for element nodes.
 *
 * @param {Node} node
 * @returns {number}
 */
export function nodeSize(node) {
    const isTextNode = node.nodeType === Node.TEXT_NODE;
    return isTextNode ? node.length : node.childNodes.length;
}
