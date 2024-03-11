/** @odoo-module **/
import { UNBREAKABLE_ROLLBACK_CODE } from '../utils/constants.js';

import {
    childNodeIndex,
    fillEmpty,
    isBlock,
    isUnbreakable,
    prepareUpdate,
    setCursorStart,
    setCursorEnd,
    setTagName,
    splitTextNode,
    toggleClass,
    isVisible,
    descendants,
    isVisibleTextNode,
    nodeSize,
} from '../utils/utils.js';

Text.prototype.oEnter = function (offset) {
    this.parentElement.oEnter(splitTextNode(this, offset), true);
};
/**
 * The whole logic can pretty much be described by this example:
 *
 *     <p><span><b>[]xt</b>ab</span>cd</p> + ENTER
 * <=> <p><span><b><br></b>[]<b>xt</b>ab</span>cd</p> + ENTER
 * <=> <p><span><b><br></b></span>[]<span><b>xt</b>ab</span>cd</p> + ENTER
 * <=> <p><span><b><br></b></span></p><p><span><b>[]xt</b>ab</span>cd</p> + SANITIZE
 * <=> <p><br></p><p><span><b>[]xt</b>ab</span>cd</p>
 *
 * Propagate the split for as long as we split an inline node, then refocus the
 * beginning of the first split node
 */
HTMLElement.prototype.oEnter = function (offset, firstSplit = true) {
    let didSplit = false;
    if (isUnbreakable(this)) {
        throw UNBREAKABLE_ROLLBACK_CODE;
    }
    let restore;
    if (firstSplit) {
        restore = prepareUpdate(this, offset);
    }

    // First split the node in two and move half the children in the clone.
    let splitEl = this.cloneNode(false);
    while (offset < this.childNodes.length) {
        splitEl.appendChild(this.childNodes[offset]);
    }
    if (isBlock(this) || splitEl.hasChildNodes()) {
        this.after(splitEl);
        if (isBlock(splitEl) || isVisible(splitEl) || splitEl.textContent === '\u200B') {
            didSplit = true;
        } else {
            splitEl.remove();
        }
    }

    // Propagate the split until reaching a block element (or continue to the
    // closest list item element if there is one).
    if (!isBlock(this) || (this.nodeName !== 'LI' && this.closest('LI'))) {
        if (this.parentElement) {
            this.parentElement.oEnter(childNodeIndex(this) + 1, !didSplit);
        } else {
            // There was no block parent element in the original chain, consider
            // this unsplittable, like an unbreakable.
            throw UNBREAKABLE_ROLLBACK_CODE;
        }
    }

    // All split have been done, place the cursor at the right position, and
    // fill/remove empty nodes.
    if (firstSplit && didSplit) {
        restore();

        let node = this;
        while (!isBlock(node) && !isVisible(node)) {
            const toRemove = node;
            node = node.parentNode;
            toRemove.remove();
        }
        fillEmpty(node);
        fillEmpty(splitEl);
        if (splitEl.tagName === 'A') {
            while (!isBlock(splitEl) && !isVisible(splitEl)) {
                const toRemove = splitEl;
                splitEl = splitEl.parentNode;
                toRemove.remove();
            }
        }
        setCursorStart(splitEl);
    }
    return splitEl;
};
/**
 * Specific behavior for headings: do not split in two if cursor at the end but
 * instead create a paragraph.
 * Cursor end of line: <h1>title[]</h1> + ENTER <=> <h1>title</h1><p>[]<br/></p>
 * Cursor in the line: <h1>tit[]le</h1> + ENTER <=> <h1>tit</h1><h1>[]le</h1>
 */
HTMLHeadingElement.prototype.oEnter = function () {
    const newEl = HTMLElement.prototype.oEnter.call(this, ...arguments);
    if (!descendants(newEl).some(isVisibleTextNode)) {
        const node = setTagName(newEl, 'P');
        node.replaceChildren(document.createElement('br'));
        setCursorStart(node);
    }
};
const isAtEdgeofLink = (link, offset) => {
    const childNodes = [...link.childNodes];
    let firstVisibleIndex = childNodes.findIndex(isVisible);
    firstVisibleIndex = firstVisibleIndex === -1 ? 0 : firstVisibleIndex;
    if (offset <= firstVisibleIndex) {
        return 'start';
    }
    let lastVisibleIndex = childNodes.reverse().findIndex(isVisible);
    lastVisibleIndex = lastVisibleIndex === -1 ? 0 : childNodes.length - lastVisibleIndex;
    if (offset >= lastVisibleIndex) {
        return 'end';
    }
    return false;
}
HTMLAnchorElement.prototype.oEnter = function (offset) {
    const edge = isAtEdgeofLink(this, offset);
    if (edge === 'start') {
        // Do not break the link at the edge: break before it.
        if (this.previousSibling) {
            return HTMLElement.prototype.oEnter.call(this.previousSibling, nodeSize(this.previousSibling));
        } else {
            const index = childNodeIndex(this);
            return HTMLElement.prototype.oEnter.call(this.parentElement, index ? index - 1 : 0);
        }
    } else if (edge === 'end') {
        // Do not break the link at the edge: break after it.
        if (this.nextSibling) {
            return HTMLElement.prototype.oEnter.call(this.nextSibling, 0);
        } else {
            return HTMLElement.prototype.oEnter.call(this.parentElement, childNodeIndex(this));
        }
    } else {
        HTMLElement.prototype.oEnter.call(this, ...arguments);
    }
}
/**
 * Same specific behavior as headings elements.
 */
HTMLQuoteElement.prototype.oEnter = HTMLHeadingElement.prototype.oEnter;
/**
 * Specific behavior for list items: deletion and unindentation when empty.
 */
HTMLLIElement.prototype.oEnter = function () {
    // If not empty list item, regular block split
    if (this.textContent) {
        const node = HTMLElement.prototype.oEnter.call(this, ...arguments);
        if (node.classList.contains('o_checked')) {
            toggleClass(node, 'o_checked');
        }
        return node;
    }
    this.oShiftTab();
};
/**
 * Specific behavior for pre: insert newline (\n) in text or insert p at end.
 */
HTMLPreElement.prototype.oEnter = function (offset) {
    if (offset < this.childNodes.length) {
        const lineBreak = document.createElement('br');
        this.insertBefore(lineBreak, this.childNodes[offset]);
        setCursorEnd(lineBreak);
    } else {
        const node = document.createElement('p');
        this.parentNode.insertBefore(node, this.nextSibling);
        fillEmpty(node);
        setCursorStart(node);
    }
};
