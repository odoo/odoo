import { closestBlock, isBlock } from "./blocks";
import {
    getDeepestPosition,
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
 * Selection of a document, as seen from one of its shadow trees.
 *
 * Used when the shadow root has no `getSelection`: the document selection is
 * retargeted to the shadow host, but its composed range still gives the
 * boundaries inside the shadow tree.
 *
 * It follows the `Selection` interface, like the selection returned by
 * `getSelection`, but only implements the part of it used by the editor.
 *
 * @see https://developer.mozilla.org/en-US/docs/Web/API/Selection
 * @see https://developer.mozilla.org/en-US/docs/Web/API/Selection/getComposedRanges
 */
class ShadowRootSelection {
    /**
     * @param {Selection} selection
     * @param {ShadowRoot} root
     */
    constructor(selection, root) {
        this.selection = selection;
        this.root = root;
    }
    /** @returns {StaticRange|undefined} */
    get composedRange() {
        let ranges;
        try {
            ranges = this.selection.getComposedRanges({ shadowRoots: [this.root] });
        } catch {
            // Older signature, taking the shadow roots as arguments.
            ranges = this.selection.getComposedRanges(this.root);
        }
        return ranges[0];
    }
    get isBackward() {
        return this.selection.direction === "backward";
    }
    get anchorNode() {
        const range = this.composedRange;
        return (this.isBackward ? range?.endContainer : range?.startContainer) ?? null;
    }
    get anchorOffset() {
        const range = this.composedRange;
        return (this.isBackward ? range?.endOffset : range?.startOffset) ?? 0;
    }
    get focusNode() {
        const range = this.composedRange;
        return (this.isBackward ? range?.startContainer : range?.endContainer) ?? null;
    }
    get focusOffset() {
        const range = this.composedRange;
        return (this.isBackward ? range?.startOffset : range?.endOffset) ?? 0;
    }
    get isCollapsed() {
        return this.composedRange?.collapsed ?? true;
    }
    get rangeCount() {
        return this.selection.rangeCount;
    }
    get type() {
        return this.selection.type;
    }
    get direction() {
        return this.selection.direction;
    }
    getRangeAt(index) {
        const staticRange = this.composedRange;
        if (index !== 0 || !staticRange) {
            return this.selection.getRangeAt(index);
        }
        const range = new Range();
        range.setStart(staticRange.startContainer, staticRange.startOffset);
        range.setEnd(staticRange.endContainer, staticRange.endOffset);
        return range;
    }
    addRange(range) {
        this.selection.addRange(range);
    }
    collapse(node, offset) {
        this.selection.collapse(node, offset);
    }
    extend(node, offset) {
        this.selection.extend(node, offset);
    }
    modify(alter, direction, granularity) {
        this.selection.modify(alter, direction, granularity);
    }
    removeAllRanges() {
        this.selection.removeAllRanges();
    }
    setBaseAndExtent(anchorNode, anchorOffset, focusNode, focusOffset) {
        this.selection.setBaseAndExtent(anchorNode, anchorOffset, focusNode, focusOffset);
    }
    toString() {
        return this.selection.toString();
    }
}

/**
 * Returns the selection of the tree of the given node.
 *
 * In a shadow tree (e.g. the livechat), the document selection is retargeted
 * to the shadow host, so it never is inside the nodes of the shadow tree.
 *
 * @param {Node} node
 * @returns {Selection|null}
 */
export function getSelectionInTree(node) {
    const root = node.getRootNode();
    const selection = node.ownerDocument.getSelection();
    if (!root.host) {
        return selection;
    }
    if (root.getSelection) {
        return root.getSelection();
    }
    if (selection?.getComposedRanges) {
        return new ShadowRootSelection(selection, root);
    }
    return selection;
}

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
        if (cursor.offset === childIndex && cursor.offset === 0) {
            // Keep cursor before the moved node if it's the first child before the move
            [cursor.node, cursor.offset] = [destParent, destIndex];
        } else if (cursor.offset === childIndex + 1 && cursor.offset === nodeSize(cursor.node)) {
            // Keep cursor after the moved node if it's the last child before the move
            [cursor.node, cursor.offset] = [destParent, destIndex + 1];
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
 * @param {Node} node
 * @param {number} offset
 * @param {"previous"|"next"} side
 * @returns {string | undefined}
 */
export function getAdjacentCharacter(node, offset, side) {
    [node, offset] = getDeepestPosition(node, offset);
    const originalBlock = closestBlock(node);
    let adjacentCharacter;
    while (!adjacentCharacter && node) {
        if (side === "previous") {
            adjacentCharacter = offset > 0 && node.textContent[offset - 1];
        } else {
            adjacentCharacter = node.textContent[offset];
        }
        if (!adjacentCharacter) {
            if (side === "previous") {
                node = previousLeaf(node, originalBlock);
                offset = node && nodeSize(node);
            } else {
                node = nextLeaf(node, originalBlock);
                offset = 0;
            }
            const characterIndex = side === "previous" ? offset - 1 : offset;
            adjacentCharacter = node && node.textContent[characterIndex];
        }
    }
    if (!node || !isContentEditable(node)) {
        return undefined;
    }
    return adjacentCharacter;
}
