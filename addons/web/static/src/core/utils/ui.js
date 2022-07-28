/** @odoo-module **/

/**
 * rough approximation of a visible element. not perfect (does not take into
 * account opacity = 0 for example), but good enough for our purpose
 *
 * @param {Element} el
 * @returns {boolean}
 */
export function isVisible(el) {
    if (el === document || el === window) {
        return true;
    }
    if (!el) {
        return false;
    }
    let _isVisible = false;
    if ("offsetWidth" in el && "offsetHeight" in el) {
        _isVisible = el.offsetWidth > 0 && el.offsetHeight > 0;
    } else if ("getBoundingClientRect" in el) {
        // for example, svgelements
        const rect = el.getBoundingClientRect();
        _isVisible = rect.width > 0 && rect.height > 0;
    }
    if (!_isVisible && getComputedStyle(el).display === "contents") {
        for (const child of el.children) {
            if (isVisible(child)) {
                return true;
            }
        }
    }
    return _isVisible;
}

/**
 * This function only exists because some tours currently rely on the fact that
 * we can click on elements with a non null width *xor* height (not both). However,
 * if one of these is 0, the element is not visible. We thus keep this function
 * to ease the transition to the more robust "isVisible" helper, which requires
 * both a non null width *and* height.
 *
 * @deprecated use isVisible instead
 * @param {Element} el
 * @returns {boolean}
 */
export function _legacyIsVisible(el) {
    if (el === document || el === window) {
        return true;
    }
    if (!el) {
        return false;
    }
    let _isVisible = false;
    if ("offsetWidth" in el && "offsetHeight" in el) {
        _isVisible = el.offsetWidth > 0 || el.offsetHeight > 0;
    } else if ("getBoundingClientRect" in el) {
        // for example, svgelements
        const rect = el.getBoundingClientRect();
        _isVisible = rect.width > 0 || rect.height > 0;
    }
    if (!_isVisible && getComputedStyle(el).display === "contents") {
        for (const child of el.children) {
            if (isVisible(child)) {
                return true;
            }
        }
    }
    return _isVisible;
}

/**
 * @param {Element} activeElement
 * @param {String} selector
 * @returns all selected and visible elements present in the activeElement
 */
export function getVisibleElements(activeElement, selector) {
    const visibleElements = [];
    /** @type {NodeListOf<HTMLElement>} */
    const elements = activeElement.querySelectorAll(selector);
    for (const el of elements) {
        if (isVisible(el)) {
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
