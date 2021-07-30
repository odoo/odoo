/** @odoo-module **/

/**
 * @param {Document} activeElement
 * @param {DOMString} selector
 * @returns all selected and visible elements present in the activeElement
 */
export function getVisibleElements(activeElement, selector) {
    const visibleElements = [];
    for (const el of activeElement.querySelectorAll(selector)) {
        const isVisible = el.offsetWidth > 0 && el.offsetHeight > 0;
        if (isVisible) {
            visibleElements.push(el);
        }
    }
    return visibleElements;
}
