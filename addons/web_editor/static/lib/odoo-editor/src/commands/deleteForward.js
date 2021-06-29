/** @odoo-module **/
import {
    childNodeIndex,
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
} from '../utils/utils.js';

Text.prototype.oDeleteForward = function (offset) {
    if (offset < this.length) {
        this.oDeleteBackward(offset + 1);
    } else {
        HTMLElement.prototype.oDeleteForward.call(this.parentNode, childNodeIndex(this) + 1);
    }
};

HTMLElement.prototype.oDeleteForward = function (offset) {
    const filterFunc = node =>
        isVisibleEmpty(node) || isContentTextNode(node) || isNotEditableNode(node);

    const firstLeafNode = findNode(rightLeafOnlyNotBlockNotEditablePath(this, offset), filterFunc);

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
