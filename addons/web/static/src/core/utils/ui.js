/**
 * @typedef Position
 * @property {number} x
 * @property {number} y
 */

/**
 * @param {Iterable<HTMLElement>} elements
 * @param {Position} targetPos
 * @returns {HTMLElement | null}
 */
export function closest(elements, targetPos) {
    let closestEl = null;
    let closestDistance = Infinity;
    for (const el of elements) {
        const rect = el.getBoundingClientRect();
        const distance = getQuadrance(rect, targetPos);
        if (!closestEl || distance < closestDistance) {
            closestEl = el;
            closestDistance = distance;
        }
    }
    return closestEl;
}

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
 * @param {DOMRect} rect
 * @param {Position} pos
 * @returns {number}
 */
export function getQuadrance(rect, pos) {
    let q = 0;
    if (pos.x < rect.x) {
        q += (rect.x - pos.x) ** 2;
    } else if (rect.x + rect.width < pos.x) {
        q += (pos.x - (rect.x + rect.width)) ** 2;
    }
    if (pos.y < rect.y) {
        q += (rect.y - pos.y) ** 2;
    } else if (rect.y + rect.height < pos.y) {
        q += (pos.y - (rect.y + rect.height)) ** 2;
    }
    return q;
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

/**
 * @param {Iterable<HTMLElement>} elements
 * @param {Partial<DOMRect>} targetRect
 * @returns {HTMLElement[]}
 */
export function touching(elements, targetRect) {
    const r1 = { x: 0, y: 0, width: 0, height: 0, ...targetRect };
    return [...elements].filter((el) => {
        const r2 = el.getBoundingClientRect();
        return (
            r2.x + r2.width >= r1.x &&
            r2.x <= r1.x + r1.width &&
            r2.y + r2.height >= r1.y &&
            r2.y <= r1.y + r1.height
        );
    });
}

// -----------------------------------------------------------------------------
// Get Tabable Elements
// -----------------------------------------------------------------------------
// TODISCUSS:
//  - leave the following in this file ?
//  - redefine this selector in tests env with ":not(#qunit *)" ?

// Following selector is based on this spec: https://html.spec.whatwg.org/multipage/interaction.html#dom-tabindex
const FOCUSABLE_SELECTORS = [
    "[tabindex]",
    "a",
    "area",
    "button",
    "frame",
    "iframe",
    "input",
    "object",
    "select",
    "textarea",
    "details > summary:nth-child(1)",
].map((sel) => `${sel}:not(:disabled)`);
const TABABLE_SELECTORS = FOCUSABLE_SELECTORS.map((sel) => `${sel}:not([tabindex="-1"])`);

/**
 * Check if an element is focusable
 *
 * @param {HTMLElement} element
 */
export function isFocusable(el) {
    return el.matches(FOCUSABLE_SELECTORS.join(",")) && isVisible(el) && !el.closest("[inert]");
}

/**
 * Returns all focusable elements in the given container.
 *
 * @param {HTMLElement} [container=document.body]
 */
export function getTabableElements(container = document.body) {
    const elements = [...container.querySelectorAll(TABABLE_SELECTORS.join(","))].filter(
        (el) => isVisible(el) && !el.closest("[inert]")
    );
    /** @type {Record<number, HTMLElement[]>} */
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

/**
 * Gives the button a loading effect by disabling it and adding a `fa` spinner
 * icon. The existing button `fa` icons will be hidden through css.
 *
 * @param {HTMLElement} btnEl - the button to disable/load
 * @return {function} a callback function that will restore the button to its
 *         initial state
 */
export function addLoadingEffect(btnEl) {
    // Note that pe-none is used alongside "disabled" so that the behavior is
    // the same on links not using the "btn" class -> pointer-events disabled.
    btnEl.classList.add("o_btn_loading", "disabled", "pe-none");
    btnEl.disabled = true;
    const loaderEl = document.createElement("span");
    loaderEl.classList.add("fa", "fa-circle-o-notch", "fa-spin", "me-2");
    btnEl.prepend(loaderEl);
    return () => {
        btnEl.classList.remove("o_btn_loading", "disabled", "pe-none");
        btnEl.disabled = false;
        loaderEl.remove();
    };
}
