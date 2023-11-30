/** @odoo-module **/
import { isUnbreakable, preserveCursor, toggleClass, isBlock, isVisible } from '../utils/utils.js';

Text.prototype.oShiftTab = function () {
    return this.parentElement.oShiftTab(0);
};

HTMLElement.prototype.oShiftTab = function (offset = undefined) {
    if (!isUnbreakable(this)) {
        return this.parentElement.oShiftTab(offset);
    }
    return false;
};

// returns: is still in a <LI> nested list
HTMLLIElement.prototype.oShiftTab = function () {
    const li = this;
    if (li.nextElementSibling) {
        const ul = li.parentElement.cloneNode(false);
        while (li.nextSibling) {
            ul.append(li.nextSibling);
        }
        if (li.parentNode.parentNode.tagName === 'LI') {
            const lip = document.createElement('li');
            toggleClass(lip, 'oe-nested');
            lip.append(ul);
            li.parentNode.parentNode.after(lip);
        } else {
            li.parentNode.after(ul);
        }
    }

    const restoreCursor = preserveCursor(this.ownerDocument);
    if (
        li.parentNode.parentNode.tagName === 'LI' &&
        !li.parentNode.parentNode.classList.contains('nav-item')
    ) {
        const ul = li.parentNode;
        const shouldRemoveParentLi = !li.previousElementSibling && !ul.previousElementSibling;
        const toremove = shouldRemoveParentLi ? ul.parentNode : null;
        ul.parentNode.after(li);
        if (toremove) {
            if (toremove.classList.contains('oe-nested')) {
                // <li>content<ul>...</ul></li>
                toremove.remove();
            } else {
                // <li class="oe-nested"><ul>...</ul></li>
                ul.remove();
            }
        }
        restoreCursor();
        return li;
    } else {
        const ul = li.parentNode;
        const dir = ul.getAttribute('dir');
        let p;
        while (li.firstChild) {
            if (isBlock(li.firstChild)) {
                p = isVisible(p) && ul.after(p) && undefined;
                ul.after(li.firstChild);
            } else {
                p = p || document.createElement('P');
                if (dir) {
                    p.setAttribute('dir', dir);
                    p.style.setProperty('text-align', ul.style.getPropertyValue('text-align'));
                }
                p.append(li.firstChild);
            }
        }
        if (isVisible(p)) ul.after(p);

        restoreCursor(new Map([[li, ul.nextSibling]]));
        li.remove();
        if (!ul.firstElementChild) {
            ul.remove();
        }
    }
    return false;
};
