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
} from '../utils/utils.js';

Text.prototype.oShiftEnter = function (offset) {
    return this.parentElement.oShiftEnter(splitTextNode(this, offset));
};

HTMLElement.prototype.oShiftEnter = function (offset, editorsBr=true) {
    const restore = prepareUpdate(this, offset);

    const brEl = document.createElement('br');
    editorsBr && brEl.classList.add("oe_linebreak");
    const brEls = [brEl];
    if (offset >= this.childNodes.length) {
        this.appendChild(brEl);
    } else {
        this.insertBefore(brEl, this.childNodes[offset]);
    }
    if (isFakeLineBreak(brEl) && getState(...leftPos(brEl), DIRECTIONS.LEFT).cType !== CTYPES.BR) {
        const brEl2 = document.createElement('br');
        editorsBr && brEl2.classList.add("oe_linebreak");
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
