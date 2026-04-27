/** @odoo-module */

/**
 * @param {String} string - Name of the drag event
 * @param {DataTransfer} dataTransfer - Object used to store data
 * @param {HTMLElement} target - Target element
 */
export function dragAndDrop(type, dataTransfer, target) {
    const fakeDragAndDrop = new Event(type, {
        bubbles: true,
        cancelable: true,
        composed: true,
    });
    fakeDragAndDrop.dataTransfer = dataTransfer;
    target.dispatchEvent(fakeDragAndDrop);
}

/**
 * @param {DataTransfer} dataTransfer - Object used to store data
 * @param {HTMLElement} target - Target element
 */
export function pasteElements(dataTransfer, target) {
    const fakePaste = new Event('paste', {
        bubbles: true,
        cancelable: true,
        composed: true,
    });
    fakePaste.clipboardData = dataTransfer;

    const sel = document.getSelection();
    sel.removeAllRanges();
    const range = document.createRange();
    const lastChild = target.lastChild;
    if (!lastChild) {
        range.setStart(target, 0);
        range.setEnd(target, 0);
    } else {
        const subLastChild = lastChild.lastChild;
        if (subLastChild) {
            if (subLastChild.nodeType === Node.ELEMENT_NODE && subLastChild.tagName === 'BR') {
                range.setStartBefore(subLastChild);
                range.setEndBefore(subLastChild);
            } else {
                range.setStartAfter(subLastChild);
                range.setEndAfter(subLastChild);
            }
        } else {
            range.setStartAfter(lastChild);
            range.setEndAfter(lastChild);
        }
    }
    const lastElementChild = target.lastElementChild;
    if (lastElementChild) {
        lastElementChild.scrollIntoView();
    } else {
        target.scrollIntoView();
    }
    sel.addRange(range);
    target.dispatchEvent(fakePaste);
}

/**
 * @param {DataTransfer} dataTransfer
 * @param {HTMLElement} editable
 */
export function replaceHtmlFieldContentWith(dataTransfer, editable) {
    editable.replaceChildren(); // Hack to avoid having a paragraph after the user's signature
    const event = new Event("paste", {
        bubbles: true,
        cancelable: true,
        composed: true,
    });
    event.clipboardData = dataTransfer;
    editable.dispatchEvent(event);
}
