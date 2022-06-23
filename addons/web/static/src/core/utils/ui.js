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

// -----------------------------------------------------------------------------
// Get Tabable Elements
// -----------------------------------------------------------------------------
// TODISCUSS:
//  - leave the following in this file ?
//  - redefine this selector in tests env with ":not(#qunit *)" ?

// Following selector is based on this spec: https://html.spec.whatwg.org/multipage/interaction.html#dom-tabindex
let TABABLE_SELECTOR = "[tabindex], a, area, button, frame, iframe, input, object, select, textarea, details > summary:nth-child(1),"
    .split(",")
    .join(':not([tabindex="-1"]):not(:disabled),');
TABABLE_SELECTOR = TABABLE_SELECTOR.slice(0, TABABLE_SELECTOR.length - 1);

export function getTabableElements(container = document.body) {
    const elements = container.querySelectorAll(TABABLE_SELECTOR);
    const byTabIndex = {};
    for (const el of [...elements]) {
        if (!byTabIndex[el.tabIndex]) {
            byTabIndex[el.tabIndex] = [];
        }
        byTabIndex[el.tabIndex].push(el);
    }

    const withTabIndexZero = byTabIndex[0] || [];
    delete byTabIndex[0];
    return [...Object.values(byTabIndex).flat(), ...withTabIndexZero];
}

export function getNextTabableElement(container = document.body) {
    const tabableElements = getTabableElements(container);
    const index = tabableElements.indexOf(document.activeElement);
    return index === -1 ? tabableElements[0] : tabableElements[index + 1] || null;
}

export function getPreviousTabableElement(container = document.body) {
    const tabableElements = getTabableElements(container);
    const index = tabableElements.indexOf(document.activeElement);
    return index === -1
        ? tabableElements[tabableElements.length - 1]
        : tabableElements[index - 1] || null;
}
