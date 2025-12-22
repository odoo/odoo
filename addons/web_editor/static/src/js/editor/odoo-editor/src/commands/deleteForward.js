/** @odoo-module **/
import { UNREMOVABLE_ROLLBACK_CODE } from '../utils/constants.js';
import {
    findNode,
    isSelfClosingElement,
    nodeSize,
    rightPos,
    getState,
    DIRECTIONS,
    CTYPES,
    leftPos,
    isIconElement,
    rightLeafOnlyNotBlockNotEditablePath,
    rightLeafOnlyPathNotBlockNotEditablePath,
    isNotEditableNode,
    splitTextNode,
    paragraphRelatedElements,
    prepareUpdate,
    isInPre,
    fillEmpty,
    setSelection,
    isZWS,
    childNodeIndex,
    boundariesOut,
    isEditorTab,
    isVisible,
    isUnbreakable,
    isEmptyBlock,
    isWhitespace,
    isVisibleTextNode,
    getOffsetAndCharSize,
    ZERO_WIDTH_CHARS,
} from '../utils/utils.js';

/**
 * Handle text node deletion for Text.oDeleteForward and Text.oDeleteBackward.
 *
 * @param {int} charSize
 * @param {int} offset
 * @param {DIRECTIONS} direction
 * @param {boolean} alreadyMoved
 */
export function deleteText(charSize, offset, direction, alreadyMoved) {
    const parentElement = this.parentElement;
    // Split around the character where the deletion occurs.
    const firstSplitOffset = splitTextNode(this, offset);
    const secondSplitOffset = splitTextNode(parentElement.childNodes[firstSplitOffset], charSize);
    const middleNode = parentElement.childNodes[firstSplitOffset];

    // Do remove the character, then restore the state of the surrounding parts.
    const restore = prepareUpdate(parentElement, firstSplitOffset, parentElement, secondSplitOffset);
    const isSpace = isWhitespace(middleNode) && !isInPre(middleNode);
    const isZWS = ZERO_WIDTH_CHARS.includes(middleNode.nodeValue);
    middleNode.remove();
    restore();

    // If the removed element was not visible content, propagate the deletion.
    const parentState = getState(parentElement, firstSplitOffset, direction);
    if (
        isZWS ||
        (isSpace &&
            (parentState.cType !== CTYPES.CONTENT || parentState.node === undefined))
    ) {
        if (direction === DIRECTIONS.LEFT) {
            parentElement.oDeleteBackward(firstSplitOffset, alreadyMoved);
        } else {
            if (isSpace && parentState.node == undefined) {
                // multiple invisible space at the start of the node
                this.oDeleteForward(offset, alreadyMoved);
            } else {
                parentElement.oDeleteForward(firstSplitOffset, alreadyMoved);
            }
        }
        if (isZWS && parentElement.isConnected) {
            fillEmpty(parentElement);
        }
        return;
    }
    fillEmpty(parentElement);
    setSelection(parentElement, firstSplitOffset);
}

Text.prototype.oDeleteForward = function (offset, alreadyMoved = false) {
    const parentElement = this.parentElement;

    if (offset === this.nodeValue.length) {
        // Delete at the end of a text node is not a specific case to handle,
        // let the element implementation handle it.
        parentElement.oDeleteForward([...parentElement.childNodes].indexOf(this) + 1);
        return;
    }
    // Get the size of the unicode character to remove.
    const [newOffset, charSize] = getOffsetAndCharSize(this.nodeValue, offset + 1, DIRECTIONS.RIGHT);
    deleteText.call(this, charSize, newOffset, DIRECTIONS.RIGHT, alreadyMoved);
};

HTMLElement.prototype.oDeleteForward = function (offset) {
    const filterFunc = node =>
        isSelfClosingElement(node) || isVisibleTextNode(node) || isNotEditableNode(node);

    const firstLeafNode = findNode(rightLeafOnlyNotBlockNotEditablePath(this, offset), filterFunc);
    if (firstLeafNode &&
        isZWS(firstLeafNode) &&
        this.parentElement.hasAttribute('data-oe-zws-empty-inline')
    ) {
        const grandparent = this.parentElement.parentElement;
        if (!grandparent) {
            return;
        }

        const parentIndex = childNodeIndex(this.parentElement);
        const restore = prepareUpdate(...boundariesOut(this.parentElement));
        this.parentElement.remove();
        restore();
        HTMLElement.prototype.oDeleteForward.call(grandparent, parentIndex);
        return;
    } else if (
        firstLeafNode &&
        firstLeafNode.nodeType === Node.TEXT_NODE &&
        firstLeafNode.textContent === '\ufeff'
    ) {
        firstLeafNode.oDeleteForward(1);
        return;
    }
    if (
        this.hasAttribute &&
        this.hasAttribute('data-oe-zws-empty-inline') &&
        (
            isZWS(this) ||
            (this.textContent === '' && this.childNodes.length === 0)
        )
    ) {
        const parent = this.parentElement;
        if (!parent) {
            return;
        }

        const index = childNodeIndex(this);
        const restore = prepareUpdate(...boundariesOut(this));
        this.remove();
        restore();
        HTMLElement.prototype.oDeleteForward.call(parent, index);
        return;
    }

    if (firstLeafNode && (isIconElement(firstLeafNode) || isNotEditableNode(firstLeafNode))) {
        const nextSibling = firstLeafNode.nextSibling;
        const nextSiblingText = nextSibling ? nextSibling.textContent : '';
        firstLeafNode.remove();
        if (isEditorTab(firstLeafNode) && nextSiblingText[0] === '\u200B') {
            // When deleting an editor tab, we need to ensure it's related ZWS
            // il deleted as well.
            nextSibling.textContent = nextSiblingText.replace('\u200B', '');
        }
        return;
    }
    if (
        firstLeafNode &&
        (firstLeafNode.nodeName !== 'BR' ||
            getState(...rightPos(firstLeafNode), DIRECTIONS.RIGHT).cType !== CTYPES.BLOCK_INSIDE)
    ) {
        firstLeafNode.oDeleteBackward(Math.min(1, nodeSize(firstLeafNode)));
        return;
    }

    let nextSibling = this.nextSibling;
    while (nextSibling && isWhitespace(nextSibling)) {
        const index = childNodeIndex(nextSibling);
        const left = getState(nextSibling, index, DIRECTIONS.LEFT).cType;
        const right = getState(nextSibling, index, DIRECTIONS.RIGHT).cType;
        if (left === CTYPES.BLOCK_OUTSIDE && right === CTYPES.BLOCK_OUTSIDE) {
            // If the next sibling is a whitespace, remove it.
            nextSibling.remove();
            nextSibling = this.nextSibling;
        } else {
            break;
        }
    }

    if (
        (
            offset === this.childNodes.length ||
            (this.childNodes.length === 1 && this.childNodes[0].tagName === 'BR')
        ) &&
        this.parentElement &&
        nextSibling &&
        ['LI', 'UL', 'OL'].includes(nextSibling.tagName)
    ) {
        const nextSiblingNestedLi = nextSibling.querySelector('li:first-child');
        if (nextSiblingNestedLi) {
            // Add the first LI from the next sibbling list to the current list.
            this.after(nextSiblingNestedLi);
            // Remove the next sibbling list if it's empty.
            if (!isVisible(nextSibling, false) || nextSibling.textContent === '') {
                nextSibling.remove();
            }
            HTMLElement.prototype.oDeleteBackward.call(nextSiblingNestedLi, 0, true);
        } else {
            HTMLElement.prototype.oDeleteBackward.call(nextSibling, 0);
        }
        return;
    }

    // Remove the nextSibling if it is a non-editable element.
    if (
        nextSibling &&
        nextSibling.nodeType === Node.ELEMENT_NODE &&
        !nextSibling.isContentEditable
    ) {
        nextSibling.remove();
        return;
    }
    const parentEl = this.parentElement;
    // Prevent the deleteForward operation since it is done at the end of an
    // enclosed editable zone (inside a non-editable zone in the editor).
    if (
        parentEl &&
        parentEl.getAttribute("contenteditable") === "true" &&
        parentEl.oid !== "root" &&
        parentEl.parentElement &&
        !parentEl.parentElement.isContentEditable &&
        paragraphRelatedElements.includes(this.tagName) &&
        !this.nextElementSibling
    ) {
        throw UNREMOVABLE_ROLLBACK_CODE;
    }
    const firstOutNode = findNode(
        rightLeafOnlyPathNotBlockNotEditablePath(
            ...(firstLeafNode ? rightPos(firstLeafNode) : [this, offset]),
        ),
        filterFunc,
    );
    if (firstOutNode) {
        // If next sibblings is an unbreadable node, and current node is empty, we
        // delete the current node and put the selection at the beginning of the
        // next sibbling.
        if (nextSibling && isUnbreakable(nextSibling) && isEmptyBlock(this)) {
            const restore = prepareUpdate(...boundariesOut(this));
            this.remove();
            restore();
            setSelection(firstOutNode, 0);
            return;
        }
        const [node, offset] = leftPos(firstOutNode);
        // If the next node is a <LI> we call directly the htmlElement
        // oDeleteBackward : because we don't want the special cases of
        // deleteBackward for LI when we comme from a deleteForward.
        if (node.tagName === 'LI') {
            HTMLElement.prototype.oDeleteBackward.call(node, offset);
            return;
        }
        node.oDeleteBackward(offset);
        return;
    }
};
