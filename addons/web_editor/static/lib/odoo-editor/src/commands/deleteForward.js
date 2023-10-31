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
    childNodeIndex, boundariesOut
} from '../utils/utils.js';

Text.prototype.oDeleteForward = function (offset, alreadyMoved = false) {
    const parentNode = this.parentNode;

    if (offset === this.nodeValue.length) {
        // Delete at the end of a text node is not a specific case to
        // handle, let the element implementation handle it.
        HTMLElement.prototype.oDeleteForward.call(this, offset, alreadyMoved);
        return;
    }

    // Get the size of the unicode character to remove.
    const charSize = [...this.nodeValue.slice(0, offset + 1)].pop().length;
    // Split around the character where the delete occurs.
    const firstSplitOffset = splitTextNode(this, offset);
    const secondSplitOffset = splitTextNode(parentNode.childNodes[firstSplitOffset], charSize);
    const middleNode = parentNode.childNodes[firstSplitOffset];

    // Do remove the character, then restore the state of the surrounding parts.
    const restore = prepareUpdate(parentNode, firstSplitOffset, parentNode, secondSplitOffset);
    const isSpace = !isVisibleStr(middleNode) && !isInPre(middleNode);
    const isZWS = middleNode.nodeValue === '\u200B';
    middleNode.remove();
    restore();

    // If the removed element was not visible content, propagate the delete.
    if (
        isZWS ||
        (isSpace &&
        getState(parentNode, firstSplitOffset, DIRECTIONS.RIGHT).cType !== CTYPES.CONTENT)
    ) {
        parentNode.oDeleteForward(firstSplitOffset, alreadyMoved);
        if (isZWS) {
            fillEmpty(parentNode);
        }
        return;
    }
    fillEmpty(parentNode);
    setSelection(parentNode, firstSplitOffset);
};

HTMLElement.prototype.oDeleteForward = function (offset) {
    const filterFunc = node =>
        isVisibleEmpty(node) || isContentTextNode(node) || isNotEditableNode(node);

    const firstLeafNode = findNode(rightLeafOnlyNotBlockNotEditablePath(this, offset), filterFunc);
    if (firstLeafNode &&
        isZWS(firstLeafNode) &&
        this.parentElement.hasAttribute('oe-zws-empty-inline')
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
        this.hasAttribute('oe-zws-empty-inline') &&
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
        firstLeafNode.remove();
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
