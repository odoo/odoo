/**
 * @typedef Position
 * @property {number} x
 * @property {number} y
 */

/**
 * @param {Iterable<HTMLElement>} elements
 * @param {Position | DOMRect} targetPos
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
 * @param {Position | DOMRect} pos
 * @returns {number}
 */
export function getQuadrance(rect, pos) {
    const isPoint = !pos.width || !pos.height;

    if (isPoint) {
        // For a point, use standard point-to-rectangle distance
        const dx = Math.max(rect.x - pos.x, 0, pos.x - (rect.x + rect.width));
        const dy = Math.max(rect.y - pos.y, 0, pos.y - (rect.y + rect.height));
        return dx ** 2 + dy ** 2;
    }

    const rectCenter = {
        x: rect.x + rect.width / 2,
        y: rect.y + rect.height / 2,
    };
    const posCenter = {
        x: pos.x + pos.width / 2,
        y: pos.y + pos.height / 2,
    };

    // Compute the distance between the centers
    const dx = Math.abs(rectCenter.x - posCenter.x);
    const dy = Math.abs(rectCenter.y - posCenter.y);
    // Gap is negative if rects are overlapping
    const gapX = dx - (rect.width + pos.width) / 2;
    const gapY = dy - (rect.height + pos.height) / 2;

    // Rectangles don't overlap (at least one gap is positive)
    if (gapX >= 0 || gapY >= 0) {
        // Return squared Euclidean distance to nearest edge
        return Math.max(0, gapX) ** 2 + Math.max(0, gapY) ** 2;
    }

    // Rectangles overlap - calculate the overlap region
    const overlapRect = {
        left: Math.max(rect.x, pos.x),
        right: Math.min(rect.x + rect.width, pos.x + pos.width),
        top: Math.max(rect.y, pos.y),
        bottom: Math.min(rect.y + rect.height, pos.y + pos.height),
    };
    const overlapArea =
        (overlapRect.right - overlapRect.left) * (overlapRect.bottom - overlapRect.top);
    const rectArea = rect.width * rect.height;
    // Normalize the overlap area by rect size to prefer smaller elements when
    // overlap area is similar (e.g., nested dropzones). Return negative
    // value so larger overlap ratios are "closer".
    // Example: two rects both have overlapArea = 15
    //   Rect A: area = 100 → ratio = 15/100 = 0.15
    //   Rect B: area = 30  → ratio = 15/30  = 0.50
    //
    // A higher ratio means we cover more of that element, so Rect B is the
    // better target. But standard min-distance logic favors smaller values so
    // we negate the ratio: -0.15 > -0.50, making Rect B "closer" and correctly
    // selected as the nearest match.
    return -(overlapArea / rectArea);
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
