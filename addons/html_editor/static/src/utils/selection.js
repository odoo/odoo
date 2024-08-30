import { closestBlock, isBlock } from "./blocks";
import {
    isContentEditable,
    isNotEditableNode,
    isSelfClosingElement,
    nextLeaf,
    previousLeaf,
} from "./dom_info";
import { isFakeLineBreak } from "./dom_state";
import { closestElement, createDOMPathGenerator } from "./dom_traversal";
import {
    DIRECTIONS,
    childNodeIndex,
    endPos,
    leftPos,
    nodeSize,
    rightPos,
    startPos,
} from "./position";

/**
 * @typedef { import("./selection_plugin").EditorSelection } EditorSelection
 */

/**
 * From selection position, checks if it is left-to-right or right-to-left.
 *
 * @param {Node} anchorNode
 * @param {number} anchorOffset
 * @param {Node} focusNode
 * @param {number} focusOffset
 * @returns {boolean} the direction of the current range if the selection not is collapsed | false
 */
export function getCursorDirection(anchorNode, anchorOffset, focusNode, focusOffset) {
    if (anchorNode === focusNode) {
        if (anchorOffset === focusOffset) {
            return false;
        }
        return anchorOffset < focusOffset ? DIRECTIONS.RIGHT : DIRECTIONS.LEFT;
    }
    return anchorNode.compareDocumentPosition(focusNode) & Node.DOCUMENT_POSITION_FOLLOWING
        ? DIRECTIONS.RIGHT
        : DIRECTIONS.LEFT;
}

/**
 * @param {EditorSelection} selection
 * @param {string} selector
 */
export function findInSelection(selection, selector) {
    const selectorInStartAncestors = closestElement(selection.startContainer, selector);
    if (selectorInStartAncestors) {
        return selectorInStartAncestors;
    } else {
        const commonElementAncestor = closestElement(selection.commonAncestorContainer);
        return (
            commonElementAncestor &&
            [...commonElementAncestor.querySelectorAll(selector)].find((node) =>
                selection.intersectsNode(node)
            )
        );
    }
}

const leftLeafOnlyInScopeNotBlockEditablePath = createDOMPathGenerator(DIRECTIONS.LEFT, {
    leafOnly: true,
    inScope: true,
    stopTraverseFunction: (node) => isNotEditableNode(node) || isBlock(node),
    stopFunction: (node) => isNotEditableNode(node) || isBlock(node),
});

const rightLeafOnlyInScopeNotBlockEditablePath = createDOMPathGenerator(DIRECTIONS.RIGHT, {
    leafOnly: true,
    inScope: true,
    stopTraverseFunction: (node) => isNotEditableNode(node) || isBlock(node),
    stopFunction: (node) => isNotEditableNode(node) || isBlock(node),
});

export function normalizeSelfClosingElement(node, offset) {
    if (isSelfClosingElement(node)) {
        // Cannot put cursor inside those elements, put it after instead.
        [node, offset] = rightPos(node);
    }
    return [node, offset];
}

export function normalizeNotEditableNode(node, offset, position = "right") {
    const editable = closestElement(node, ".odoo-editor-editable");
    let closest = closestElement(node);
    while (closest && closest !== editable && !closest.isContentEditable) {
        [node, offset] = position === "right" ? rightPos(node) : leftPos(node);
        closest = node;
    }
    return [node, offset];
}

export function normalizeCursorPosition(node, offset, position = "right") {
    [node, offset] = normalizeSelfClosingElement(node, offset);
    [node, offset] = normalizeNotEditableNode(node, offset, position);
    // todo @phoenix: we should maybe remove it
    // // Be permissive about the received offset.
    // offset = Math.min(Math.max(offset, 0), nodeSize(node));
    return [node, offset];
}

export function normalizeFakeBR(node, offset) {
    const prevNode = node.nodeType === Node.ELEMENT_NODE && node.childNodes[offset - 1];
    if (prevNode && prevNode.nodeName === "BR" && isFakeLineBreak(prevNode)) {
        // If trying to put the cursor on the right of a fake line break, put
        // it before instead.
        offset--;
    }
    return [node, offset];
}

/**
 * From a given position, returns the normalized version.
 *
 * E.g. <b>abc</b>[]def -> <b>abc[]</b>def
 *
 * @param {Node} node
 * @param {number} offset
 * @returns { [Node, number] }
 */
export function normalizeDeepCursorPosition(node, offset) {
    // Put the cursor in deepest inline node around the given position if
    // possible.
    let el;
    let elOffset;
    if (node.nodeType === Node.ELEMENT_NODE) {
        el = node;
        elOffset = offset;
    } else if (node.nodeType === Node.TEXT_NODE) {
        if (offset === 0) {
            el = node.parentNode;
            elOffset = childNodeIndex(node);
        } else if (offset === node.length) {
            el = node.parentNode;
            elOffset = childNodeIndex(node) + 1;
        }
    }
    if (el) {
        const leftInlineNode = leftLeafOnlyInScopeNotBlockEditablePath(el, elOffset).next().value;
        let leftVisibleEmpty = false;
        if (leftInlineNode) {
            leftVisibleEmpty =
                isSelfClosingElement(leftInlineNode) || !isContentEditable(leftInlineNode);
            [node, offset] = leftVisibleEmpty ? rightPos(leftInlineNode) : endPos(leftInlineNode);
        }
        if (!leftInlineNode || leftVisibleEmpty) {
            const rightInlineNode = rightLeafOnlyInScopeNotBlockEditablePath(el, elOffset).next()
                .value;
            if (rightInlineNode) {
                const closest = closestElement(rightInlineNode);
                const rightVisibleEmpty =
                    isSelfClosingElement(rightInlineNode) || !closest || !closest.isContentEditable;
                if (!(leftVisibleEmpty && rightVisibleEmpty)) {
                    [node, offset] = rightVisibleEmpty
                        ? leftPos(rightInlineNode)
                        : startPos(rightInlineNode);
                }
            }
        }
    }
    return [node, offset];
}

function updateCursorBeforeMove(destParent, destIndex, node, cursor) {
    if (cursor.node === destParent && cursor.offset >= destIndex) {
        // Update cursor at destination
        cursor.offset += 1;
    } else if (cursor.node === node.parentNode) {
        const childIndex = childNodeIndex(node);
        // Update cursor at origin
        if (cursor.offset === childIndex) {
            // Keep pointing to the moved node
            [cursor.node, cursor.offset] = [destParent, destIndex];
        } else if (cursor.offset > childIndex) {
            cursor.offset -= 1;
        }
    }
}

function updateCursorBeforeRemove(node, cursor) {
    if (node.contains(cursor.node)) {
        [cursor.node, cursor.offset] = [node.parentNode, childNodeIndex(node)];
    } else if (cursor.node === node.parentNode && cursor.offset > childNodeIndex(node)) {
        cursor.offset -= 1;
    }
}

function updateCursorBeforeUnwrap(node, cursor) {
    if (cursor.node === node) {
        [cursor.node, cursor.offset] = [node.parentNode, cursor.offset + childNodeIndex(node)];
    } else if (cursor.node === node.parentNode && cursor.offset > childNodeIndex(node)) {
        cursor.offset += nodeSize(node) - 1;
    }
}

function updateCursorBeforeMergeIntoPreviousSibling(node, cursor) {
    if (cursor.node === node) {
        cursor.node = node.previousSibling;
        cursor.offset += node.previousSibling.childNodes.length;
    } else if (cursor.node === node.parentNode) {
        const childIndex = childNodeIndex(node);
        if (cursor.offset === childIndex) {
            cursor.node = node.previousSibling;
            cursor.offset = node.previousSibling.childNodes.length;
        } else if (cursor.offset > childIndex) {
            cursor.offset--;
        }
    }
}

/** @typedef {import("@html_editor/core/selection_plugin").Cursor} Cursor */

export const callbacksForCursorUpdate = {
    /** @type {(node: Node) => (cursor: Cursor) => void} */
    remove: (node) => (cursor) => updateCursorBeforeRemove(node, cursor),
    /** @type {(ref: HTMLElement, node: Node) => (cursor: Cursor) => void} */
    before: (ref, node) => (cursor) =>
        updateCursorBeforeMove(ref.parentNode, childNodeIndex(ref), node, cursor),
    /** @type {(ref: HTMLElement, node: Node) => (cursor: Cursor) => void} */
    after: (ref, node) => (cursor) =>
        updateCursorBeforeMove(ref.parentNode, childNodeIndex(ref) + 1, node, cursor),
    /** @type {(ref: HTMLElement, node: Node) => (cursor: Cursor) => void} */
    append: (to, node) => (cursor) =>
        updateCursorBeforeMove(to, to.childNodes.length, node, cursor),
    /** @type {(ref: HTMLElement, node: Node) => (cursor: Cursor) => void} */
    prepend: (to, node) => (cursor) => updateCursorBeforeMove(to, 0, node, cursor),
    /** @type {(node: HTMLElement) => (cursor: Cursor) => void} */
    unwrap: (node) => (cursor) => updateCursorBeforeUnwrap(node, cursor),
    /** @type {(node: HTMLElement) => (cursor: Cursor) => void} */
    merge: (node) => (cursor) => updateCursorBeforeMergeIntoPreviousSibling(node, cursor),
};

/**
 * @param {Selection} selection
 * @param {"previous"|"next"} side
 * @param {HTMLElement} editable
 * @returns {string | undefined}
 */
export function getAdjacentCharacter(selection, side, editable) {
    let { focusNode, focusOffset } = selection;
    const originalBlock = closestBlock(focusNode);
    let adjacentCharacter;
    while (!adjacentCharacter && focusNode) {
        if (side === "previous") {
            // @todo: this might be wrong in the first time, as focus node might not be a leaf.
            adjacentCharacter = focusOffset > 0 && focusNode.textContent[focusOffset - 1];
        } else {
            adjacentCharacter = focusNode.textContent[focusOffset];
        }
        if (!adjacentCharacter) {
            if (side === "previous") {
                focusNode = previousLeaf(focusNode, editable);
                focusOffset = focusNode && nodeSize(focusNode);
            } else {
                focusNode = nextLeaf(focusNode, editable);
                focusOffset = 0;
            }
            const characterIndex = side === "previous" ? focusOffset - 1 : focusOffset;
            adjacentCharacter = focusNode && focusNode.textContent[characterIndex];
        }
    }
    if (!focusNode || !isContentEditable(focusNode) || closestBlock(focusNode) !== originalBlock) {
        return undefined;
    }
    return adjacentCharacter;
}
