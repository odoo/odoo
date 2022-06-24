/** @odoo-module **/
import { UNBREAKABLE_ROLLBACK_CODE, UNREMOVABLE_ROLLBACK_CODE } from '../utils/constants.js';
import {
    boundariesOut,
    childNodeIndex,
    CTGROUPS,
    CTYPES,
    DIRECTIONS,
    endPos,
    fillEmpty,
    getState,
    isBlock,
    isInPre,
    isUnremovable,
    isVisible,
    isVisibleStr,
    leftPos,
    rightPos,
    moveNodes,
    nodeSize,
    prepareUpdate,
    setSelection,
    splitTextNode,
    isMediaElement,
    isVisibleEmpty,
    isNotEditableNode,
    createDOMPathGenerator,
} from '../utils/utils.js';

Text.prototype.oDeleteBackward = function (offset, alreadyMoved = false) {
    const parentNode = this.parentNode;

    if (!offset) {
        // Backspace at the beginning of a text node is not a specific case to
        // handle, let the element implementation handle it.
        HTMLElement.prototype.oDeleteBackward.call(this, offset, alreadyMoved);
        return;
    }

    // Get the size of the unicode character to remove.
    const charSize = [...this.nodeValue.slice(0, offset)].pop().length;
    // Split around the character where the backspace occurs.
    const firstSplitOffset = splitTextNode(this, offset - charSize);
    const secondSplitOffset = splitTextNode(parentNode.childNodes[firstSplitOffset], charSize);
    const middleNode = parentNode.childNodes[firstSplitOffset];

    // Do remove the character, then restore the state of the surrounding parts.
    const restore = prepareUpdate(parentNode, firstSplitOffset, parentNode, secondSplitOffset);
    const isSpace = !isVisibleStr(middleNode) && !isInPre(middleNode);
    const isZWS = middleNode.nodeValue === '\u200B';
    middleNode.remove();
    restore();

    // If the removed element was not visible content, propagate the backspace.
    if (
        isZWS ||
        isSpace &&
        getState(parentNode, firstSplitOffset, DIRECTIONS.LEFT).cType !== CTYPES.CONTENT
    ) {
        parentNode.oDeleteBackward(firstSplitOffset, alreadyMoved);
        if (isZWS) {
            fillEmpty(parentNode);
        }
        return;
    }

    fillEmpty(parentNode);
    setSelection(parentNode, firstSplitOffset);
};

const isDeletable = (node) => {
    return isMediaElement(node) || isNotEditableNode(node);
}

HTMLElement.prototype.oDeleteBackward = function (offset, alreadyMoved = false, offsetLimit) {
    const contentIsZWS = this.textContent === '\u200B';
    let moveDest;
    if (offset) {
        const leftNode = this.childNodes[offset - 1];
        if (isUnremovable(leftNode)) {
            throw UNREMOVABLE_ROLLBACK_CODE;
        }
        if (
            isDeletable(leftNode)
        ) {
            leftNode.remove();
            return;
        }
        if (!isBlock(leftNode) || isVisibleEmpty(leftNode)) {
            /**
             * Backspace just after an inline node, convert to backspace at the
             * end of that inline node.
             *
             * E.g. <p>abc<i>def</i>[]</p> + BACKSPACE
             * <=>  <p>abc<i>def[]</i></p> + BACKSPACE
             */
            leftNode.oDeleteBackward(nodeSize(leftNode), alreadyMoved);
            return;
        }

        /**
         * Backspace just after an block node, we have to move any inline
         * content after it, up to the next block. If the cursor is between
         * two blocks, this is a theoretical case: just do nothing.
         *
         * E.g. <p>abc</p>[]de<i>f</i><p>ghi</p> + BACKSPACE
         * <=>  <p>abcde<i>f</i></p><p>ghi</p>
         */
        alreadyMoved = true;
        moveDest = endPos(leftNode);
    } else {
        if (isUnremovable(this)) {
            throw UNREMOVABLE_ROLLBACK_CODE;
        }
        const parentEl = this.parentNode;

        if (!isBlock(this) || isVisibleEmpty(this)) {
            /**
             * Backspace at the beginning of an inline node, nothing has to be
             * done: propagate the backspace. If the node was empty, we remove
             * it before.
             *
             * E.g. <p>abc<b></b><i>[]def</i></p> + BACKSPACE
             * <=>  <p>abc<b>[]</b><i>def</i></p> + BACKSPACE
             * <=>  <p>abc[]<i>def</i></p> + BACKSPACE
             */
            const parentOffset = childNodeIndex(this);

            if (!nodeSize(this) || contentIsZWS) {
                const visible = isVisible(this) && !contentIsZWS;
                const restore = prepareUpdate(...boundariesOut(this));
                this.remove();
                restore();

                fillEmpty(parentEl);

                if (visible) {
                    // TODO this handle BR/IMG/etc removals../ to see if we
                    // prefer to have a dedicated handler for every possible
                    // HTML element or if we let this generic code handle it.
                    setSelection(parentEl, parentOffset);
                    return;
                }
            }
            parentEl.oDeleteBackward(parentOffset, alreadyMoved);
            return;
        }

        /**
         * Backspace at the beginning of a block node, we have to move the
         * inline content at its beginning outside of the element and propagate
         * to the left block if any.
         *
         * E.g. (prev == block)
         *      <p>abc</p><div>[]def<p>ghi</p></div> + BACKSPACE
         * <=>  <p>abc</p>[]def<div><p>ghi</p></div> + BACKSPACE
         *
         * E.g. (prev != block)
         *      abc<div>[]def<p>ghi</p></div> + BACKSPACE
         * <=>  abc[]def<div><p>ghi</p></div>
         */
        moveDest = leftPos(this);
    }

    const domPathGenerator = createDOMPathGenerator(DIRECTIONS.LEFT, {
        leafOnly: true,
        stopTraverseFunction: isDeletable,
    });
    const domPath = domPathGenerator(this, offset)
    const leftNode = domPath.next().value;
    if (leftNode && isDeletable(leftNode)) {
        const [parent, offset] = rightPos(leftNode);
        return parent.oDeleteBackward(offset, alreadyMoved);
    }
    let node = this.childNodes[offset];
    const nextSibling = this.nextSibling;
    let currentNodeIndex = offset;

    // `offsetLimit` will ensure we never move nodes that were not initialy in the element
    //  => when Deleting and merging an element the containing node will temporary be hosted
    //  in the common parent beside possible other nodes. We don't want to touch those others node when merging
    //  two html elements
    //  ex : <div>12<p>ab[]</p><p>cd</p>34</div> should never touch the 12 and 34 text node.
    if (offsetLimit === undefined) {
        while (node && !isBlock(node)) {
            node = node.nextSibling;
            currentNodeIndex++;
        }
    } else {
        currentNodeIndex = offsetLimit;
    }
    let [cursorNode, cursorOffset] = moveNodes(...moveDest, this, offset, currentNodeIndex);
    setSelection(cursorNode, cursorOffset);

    // Propagate if this is still a block on the left of where the nodes were
    // moved.
    if (
        cursorNode.nodeType === Node.TEXT_NODE &&
        (cursorOffset === 0 || cursorOffset === cursorNode.length)
    ) {
        cursorOffset = childNodeIndex(cursorNode) + (cursorOffset === 0 ? 0 : 1);
        cursorNode = cursorNode.parentNode;
    }
    if (cursorNode.nodeType !== Node.TEXT_NODE) {
        const { cType } = getState(cursorNode, cursorOffset, DIRECTIONS.LEFT);
        if (cType & CTGROUPS.BLOCK && (!alreadyMoved || cType === CTYPES.BLOCK_OUTSIDE)) {
            cursorNode.oDeleteBackward(cursorOffset, alreadyMoved, cursorOffset + currentNodeIndex - offset);
        } else if (!alreadyMoved) {
            // When removing a block node adjacent to a inline node,
            // we need to ensure the block node induced line break are kept with a <br>.
            // ex : <div>a<span>b</span><p>[]c</p>d</div> => deleteBakward
            // =>   <div>a<span>b</span>[]c<br>d</div>
            // In this case we cannot simply merge the <p> content into the div parent
            // or we would loose the line break located after the <p>.
            const cursorNodeNode = cursorNode.childNodes[cursorOffset];
            const cursorNodeRightNode = cursorNodeNode ? cursorNodeNode.nextSibling : undefined;
            if (cursorNodeRightNode &&
                cursorNodeRightNode.nodeType === Node.TEXT_NODE &&
                nextSibling === cursorNodeRightNode) {
                moveDest[0].insertBefore(document.createElement('br'), cursorNodeRightNode);
            }
        }
    }
};

HTMLLIElement.prototype.oDeleteBackward = function (offset, alreadyMoved = false) {
    if (offset > 0 || this.previousElementSibling) {
        // If backspace inside li content or if the li is not the first one,
        // it behaves just like in a normal element.
        HTMLElement.prototype.oDeleteBackward.call(this, offset, alreadyMoved);
        return;
    }
    this.oShiftTab(offset);
};

HTMLBRElement.prototype.oDeleteBackward = function (offset, alreadyMoved = false) {
    const parentOffset = childNodeIndex(this);
    const rightState = getState(this.parentElement, parentOffset + 1, DIRECTIONS.RIGHT).cType;
    if (rightState & CTYPES.BLOCK_INSIDE) {
        this.parentElement.oDeleteBackward(parentOffset, alreadyMoved);
    } else {
        HTMLElement.prototype.oDeleteBackward.call(this, offset, alreadyMoved);
    }
};
