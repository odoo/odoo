/** @odoo-module **/
import { createList, getListMode, isBlock, preserveCursor, toggleClass } from '../utils/utils.js';

Text.prototype.oTab = function () {
    return this.parentElement.oTab(0);
};

HTMLElement.prototype.oTab = function (offset) {
    if (!isBlock(this)) {
        return this.parentElement.oTab(offset);
    }
    return false;
};

HTMLLIElement.prototype.oTab = function () {
    const lip = document.createElement('li');
    const destul =
        (this.previousElementSibling && this.previousElementSibling.querySelector('ol, ul')) ||
        (this.nextElementSibling && this.nextElementSibling.querySelector('ol, ul')) ||
        this.closest('ul, ol');

    const ul = createList(getListMode(destul));
    lip.append(ul);

    const cr = preserveCursor(this.ownerDocument);
    toggleClass(lip, 'oe-nested');
    this.before(lip);
    ul.append(this);
    cr();
    return true;
};
