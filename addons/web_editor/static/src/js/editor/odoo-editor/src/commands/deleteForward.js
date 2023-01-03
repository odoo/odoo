/** @odoo-module **/
import {
    findNode,
    isContentTextNode,
    isVisibleEmpty,
    nodeSize,
    rightPos,
    getState,
    DIRECTIONS,
    CTYPES,
    leftPos,
    isFontAwesome,
    rightLeafOnlyNotBlockNotEditablePath,
    rightLeafOnlyPathNotBlockNotEditablePath,
    isNotEditableNode,
    splitTextNode,
    prepareUpdate,
    isVisibleStr,
    isInPre,
    fillEmpty,
    setSelection,
    isZWS,
    childNodeIndex,
    boundariesOut,
    isEditorTab,
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
    const isSpace = !isVisibleStr(middleNode) && !isInPre(middleNode);
    const isZWS = middleNode.nodeValue === '\u200B';
    middleNode.remove();
    restore();

    // If the removed element was not visible content, propagate the deletion.
    if (
        isZWS ||
        (isSpace &&
            getState(parentElement, firstSplitOffset, direction).cType !== CTYPES.CONTENT)
    ) {
        if(direction === DIRECTIONS.LEFT) {
            parentElement.oDeleteBackward(firstSplitOffset, alreadyMoved);
        } else {
            parentElement.oDeleteForward(firstSplitOffset, alreadyMoved);
        }
        if (isZWS) {
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
    const charSize = [...this.nodeValue.slice(0, offset + 1)].pop().length;
    deleteText.call(this, charSize, offset, DIRECTIONS.RIGHT, alreadyMoved);
};

HTMLElement.prototype.oDeleteForward = function (offset) {
    const filterFunc = node =>
        isVisibleEmpty(node) || isContentTextNode(node) || isNotEditableNode(node);

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

    if (firstLeafNode && (isFontAwesome(firstLeafNode) || isNotEditableNode(firstLeafNode))) {
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
    const firstOutNode = findNode(
        rightLeafOnlyPathNotBlockNotEditablePath(
            ...(firstLeafNode ? rightPos(firstLeafNode) : [this, offset]),
        ),
        filterFunc,
    );
    if (firstOutNode) {
        const [node, offset] = leftPos(firstOutNode);
        node.oDeleteBackward(offset);
        return;
    }
};
