/** @odoo-module **/
import {
    childNodeIndex,
    getListMode,
    isBlock,
    preserveCursor,
    setTagName,
    toggleClass,
    insertListAfter,
    getAdjacents,
    closestElement,
} from '../utils/utils.js';

Text.prototype.oToggleList = function (offset, mode) {
    // Create a new list if textNode is inside a nav-item list
    if (closestElement(this, 'li').classList.contains('nav-item')) {
        const restoreCursor = preserveCursor(this.ownerDocument);
        insertListAfter(this, mode, [this]);
        restoreCursor();
    } else {
        this.parentElement.oToggleList(childNodeIndex(this), mode);
    }
};

HTMLElement.prototype.oToggleList = function (offset, mode = 'UL') {
    if (!isBlock(this)) {
        return this.parentElement.oToggleList(childNodeIndex(this));
    }
    const closestLi = this.closest('li');
    // Do not toggle nav-item list as they don't behave like regular list items
    if (closestLi && !closestLi.classList.contains('nav-item')) {
        return closestLi.oToggleList(0, mode);
    }
    const restoreCursor = preserveCursor(this.ownerDocument);
    if (this.oid === 'root') {
        const callingNode = this.childNodes[offset];
        const group = getAdjacents(callingNode, n => !isBlock(n));
        insertListAfter(callingNode, mode, [group]);
        restoreCursor();
    } else {
        const list = insertListAfter(this, mode, [this]);
        if (this.hasAttribute('dir')) {
            list.setAttribute('dir', this.getAttribute('dir'));
        }
        restoreCursor(new Map([[this, list.firstElementChild]]));
    }
};

HTMLParagraphElement.prototype.oToggleList = function (offset, mode = 'UL') {
    const restoreCursor = preserveCursor(this.ownerDocument);
    const list = insertListAfter(this, mode, [[...this.childNodes]]);
    const classList = [...list.classList];
    for (const attribute of this.attributes) {
        if (attribute.name === 'class' && attribute.value && list.className) {
            list.className = `${list.className} ${attribute.value}`;
        } else {
            list.setAttribute(attribute.name, attribute.value);
        }
    }
    for (const className of classList) {
        list.classList.toggle(className, true); // restore list classes
    }
    this.remove();

    restoreCursor(new Map([[this, list.firstChild]]));
    return true;
};

HTMLLIElement.prototype.oToggleList = function (offset, mode) {
    const pnode = this.closest('ul, ol');
    if (!pnode) return;
    const restoreCursor = preserveCursor(this.ownerDocument);
    const listMode = getListMode(pnode) + mode;
    if (['OLCL', 'ULCL'].includes(listMode)) {
        pnode.classList.add('o_checklist');
        for (let li = pnode.firstElementChild; li !== null; li = li.nextElementSibling) {
            if (li.style.listStyle != 'none') {
                li.style.listStyle = null;
                if (!li.style.all) li.removeAttribute('style');
            }
        }
        setTagName(pnode, 'UL');
    } else if (['CLOL', 'CLUL'].includes(listMode)) {
        toggleClass(pnode, 'o_checklist');
        setTagName(pnode, mode);
    } else if (['OLUL', 'ULOL'].includes(listMode)) {
        setTagName(pnode, mode);
    } else {
        // toggle => remove list
        let node = this;
        while (node) {
            node = node.oShiftTab(offset);
        }
    }

    restoreCursor();
    return false;
};

HTMLTableCellElement.prototype.oToggleList = function (offset, mode) {
    const restoreCursor = preserveCursor(this.ownerDocument);
    const callingNode = this.childNodes[offset];
    const group = getAdjacents(callingNode, n => !isBlock(n));
    insertListAfter(callingNode, mode, [group]);
    restoreCursor();
};
