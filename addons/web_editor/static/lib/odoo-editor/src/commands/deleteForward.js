/** @odoo-module **/
import {
    childNodeIndex,
    findNode,
    isContentTextNode,
    isVisibleEmpty,
    nodeSize,
    rightDeepOnlyPath,
    rightDeepOnlyInlinePath,
    rightPos,
    getState,
    DIRECTIONS,
    CTYPES,
    leftPos,
    isFontAwesome,
} from '../utils/utils.js';

Text.prototype.oDeleteForward = function (offset) {
    if (offset < this.length) {
        this.oDeleteBackward(offset + 1);
    } else {
        HTMLElement.prototype.oDeleteForward.call(this.parentNode, childNodeIndex(this) + 1);
    }
};

HTMLElement.prototype.oDeleteForward = function (offset) {
    const filterFunc = node => isVisibleEmpty(node) || isContentTextNode(node);

    const firstInlineNode = findNode(rightDeepOnlyInlinePath(this, offset), filterFunc);
    if (isFontAwesome(firstInlineNode && firstInlineNode.parentElement)) {
        firstInlineNode.parentElement.remove();
        return;
    }
    if (
        firstInlineNode &&
        (firstInlineNode.nodeName !== 'BR' ||
            getState(...rightPos(firstInlineNode), DIRECTIONS.RIGHT).cType !== CTYPES.BLOCK_INSIDE)
    ) {
        firstInlineNode.oDeleteBackward(Math.min(1, nodeSize(firstInlineNode)));
        return;
    }
    const firstOutNode = findNode(
        rightDeepOnlyPath(...(firstInlineNode ? rightPos(firstInlineNode) : [this, offset])),
        filterFunc,
    );
    if (firstOutNode) {
        const [node, offset] = leftPos(firstOutNode);
        node.oDeleteBackward(offset);
        return;
    }
};
