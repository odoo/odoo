/** @odoo-module **/
import {
    CTYPES,
    DIRECTIONS,
    isFakeLineBreak,
    prepareUpdate,
    rightPos,
    setSelection,
    getState,
    leftPos,
    splitTextNode,
    isBlock,
} from '../utils/utils.js';

Text.prototype.oShiftEnter = function (offset) {
    return this.parentElement.oShiftEnter(splitTextNode(this, offset));
};

HTMLElement.prototype.oShiftEnter = function (offset) {
    const restore = prepareUpdate(this, offset);

    const brEl = document.createElement('br');
    const brEls = [brEl];
    if (offset >= this.childNodes.length) {
        this.appendChild(brEl);
    } else {
        this.insertBefore(brEl, this.childNodes[offset]);
    }
    if (isFakeLineBreak(brEl) && getState(...leftPos(brEl), DIRECTIONS.LEFT).cType !== CTYPES.BR) {
        const brEl2 = document.createElement('br');
        brEl.before(brEl2);
        brEls.unshift(brEl2);
    }

    restore();

    for (const el of brEls) {
        if (el.parentNode) {
            setSelection(...rightPos(el));
            break;
        }
    }

    return brEls;
};

/**
 * Special behavior for links: do not add a line break at its edges, but rather
 * move the line break outside the link.
 */
HTMLAnchorElement.prototype.oShiftEnter = function () {
    const brs = HTMLElement.prototype.oShiftEnter.call(this, ...arguments);
    const anchor = brs[0].parentElement;
    let firstChild = anchor.firstChild;
    if (firstChild && firstChild.nodeType === Node.TEXT_NODE && firstChild.textContent === '\uFEFF') {
        firstChild = anchor.childNodes[1];
    }
    let lastChild = anchor.lastChild;
    if (lastChild && lastChild.nodeType === Node.TEXT_NODE && lastChild.textContent === '\uFEFF') {
        lastChild = anchor.childNodes.length > 1 && anchor.childNodes[anchor.childNodes.length - 2];
    }
    if (brs.includes(firstChild)) {
        brs.forEach(br => anchor.before(br));
    } else if (brs.includes(lastChild)) {
        const brToRemove = isBlock(anchor) && brs.pop();
        brs.forEach(br => anchor.after(br));
        if (brToRemove) {
            // When the anchor tag is block, keeping the two `br` tags
            // would have resulted into two new lines instead of one.
            brToRemove.remove();
            setSelection(...leftPos(brs[0]));
        } else {
            setSelection(...rightPos(brs[0]));
        }
    }
}
