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
const TABABLE_SELECTOR = [
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
]
    .map((sel) => `${sel}:not([tabindex="-1"]):not(:disabled)`)
    .join(",");

/**
 * Returns all focusable elements in the given container.
 *
 * @param {HTMLElement} [container=document.body]
 */
export function getTabableElements(container = document.body) {
    const elements = [...container.querySelectorAll(TABABLE_SELECTOR)].filter(isVisible);
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
    loaderEl.classList.add("fa", "fa-refresh", "fa-spin", "me-2");
    btnEl.prepend(loaderEl);
    return () => {
        btnEl.classList.remove("o_btn_loading", "disabled", "pe-none");
        btnEl.disabled = false;
        loaderEl.remove();
    };
}

/**
 * Renders a button with standard odoo template. This does not use any xml
 * template to avoid forcing the frontend part to lazy load a xml file for
 * each widget which might want to create a simple button.
 *
 * @param {Object} options
 * @param {Object} [options.attrs] - Attributes to put on the button element
 * @param {string} [options.attrs.type='button']
 * @param {string} [options.attrs.class='btn-secondary']
 *        Note: automatically completed with "btn btn-X"
 *        (@see options.size for the value of X)
 * @param {string} [options.size] - @see options.attrs.class
 * @param {string} [options.icon]
 *        The specific fa icon class (for example "fa-home") or an URL for
 *        an image to use as icon.
 * @param {string} [options.text] - the button's text
 * @returns {HTMLElement}
 */
export function renderButton(options) {
    const params = Object.assign({
        type: 'button',
    }, options.attrs || {});

    let extraClasses = params.class;
    if (extraClasses) {
        // If we got extra classes, check if old oe_highlight/oe_link
        // classes are given and switch them to the right classes (those
        // classes have no style associated to them anymore).
        // TODO ideally this should be dropped at some point.
        extraClasses = extraClasses.replace(/\boe_highlight\b/g, 'btn-primary')
            .replace(/\boe_link\b/g, 'btn-link');
    }

    params.class = 'btn';
    if (options.size) {
        params.class += ' btn-' + options.size;
    }
    params.class += ' ' + (extraClasses || 'btn-secondary');

    const button = document.createElement('button');
    for (const key in params) {
        if (params.hasOwnProperty(key)) {
            if (key === 'disabled' && params[key] === undefined) {
                continue;
            }
            button.setAttribute(key, params[key]);
        }
    }

    if (options.icon) {
        let iconElement;
        if (options.icon.substr(0, 3) === 'fa-') {
            iconElement = document.createElement('i');
            iconElement.className = 'fa fa-fw o_button_icon ' + options.icon;
        } else {
            iconElement = document.createElement('img');
            iconElement.src = options.icon;
        }
        button.appendChild(iconElement);
    }

    if (options.text) {
        const textElement = document.createElement('span');
        textElement.textContent = options.text;
        button.appendChild(textElement);
    }

    button.offset = offset;

    return button;
}

/**
 * Calculates the offset position of the element relative to the document.
 *
 * @param {Object} options - Options for calculating the offset
 * @returns {Array|Object} - Offset position(s) of the element
 */
function offset(elements, options) {
    if (!elements.length) {
        elements = [elements];
    }
    if (options) {
        elements.forEach(function (element) {
            setOffset(element, options);
        });
        return;
    }

    const results = [];
    elements.forEach(function (elem) {

        if (!elem) {
            return;
        }

        if (!elem.getClientRects().length) {
            results.push({ top: 0, left: 0 });
        } else {
            const rect = elem.getBoundingClientRect();
            const win = elem.ownerDocument.defaultView;
            results.push({
                top: rect.top + win.pageYOffset,
                left: rect.left + win.pageXOffset
            });
        }
    });

    return results.length === 1 ? results[0] : results;
}

/**
 * Adjusts the position of an element relative to its offset parent or specified coordinates.
 *
 * @param {HTMLElement} elem - The element whose position is to be adjusted.
 * @param {Object} options - An object containing the new top and left positions, 
 * or a function that returns such an object.
 * @param {number} [options.top] - The new top position of the element.
 * @param {number} [options.left] - The new left position of the element.
 * @param {Function} [options.using] - A function to execute after the position is set, 
 * with the calculated position object passed as its argument.
 */
function setOffset(elem, options) {
    let curPosition, curLeft, curCSSTop, curTop, curOffset, curCSSLeft, calculatePosition,
        position = getComputedStyle(elem).position,
        props = {};

    if (position === "static") {
        elem.style.position = "relative";
    }

    curOffset = offset(elem);
    curCSSTop = getComputedStyle(elem).top;
    curCSSLeft = getComputedStyle(elem).left;
    calculatePosition = (position === "absolute" || position === "fixed") &&
        (curCSSTop === "auto" || curCSSLeft === "auto");

    if (calculatePosition) {
        curPosition = position(elem);
        curTop = curPosition.top;
        curLeft = curPosition.left;
    } else {
        curTop = parseFloat(curCSSTop) || 0;
        curLeft = parseFloat(curCSSLeft) || 0;
    }

    if (typeof options === 'function') {
        options = options(elem, Object.assign({}, curOffset));
    }

    if (options.top != null) {
        props.top = (options.top - curOffset.top) + curTop;
    }
    if (options.left != null) {
        props.left = (options.left - curOffset.left) + curLeft;
    }

    if (typeof options.using === 'function') {
        options.using(elem, props);
    } else {
        Object.keys(props).forEach(function(key) {
            elem.style[key] = props[key] + 'px';
        });
    }
}

/**
 * @param {HTMLElement|string} el - the element to scroll to. If "el" is a
 *      string, it must be a valid selector of an element in the DOM or
 *      '#top' or '#bottom'. If it is an HTML element, it must be present
 *      in the DOM.
 *      Limitation: if the element is using a fixed position, this
 *      function cannot work except if is the header (el is then either a
 *      string set to '#top' or an HTML element with the "top" id) or the
 *      footer (el is then a string set to '#bottom' or an HTML element
 *      with the "bottom" id) for which exceptions have been made.
 * @param {number} [options] - options for the scroll behavior
 * @param {number} [options.extraOffset=0]
 *      extra offset to add on top of the automatic one (the automatic one
 *      being computed based on fixed header sizes)
 * @param {number} [options.forcedOffset]
 *      offset used instead of the automatic one (extraOffset will be
 *      ignored too)
 * @param {HTMLElement} [options.scrollable] the element to scroll
 * @return {Promise}
 */
export function scrollTo(el, options = {}) {
    if (!el) {
        throw new Error("The scrollTo function was called without any given element");
    }
    if (typeof el === 'string') {
        el = document.querySelector(el);
    }
    const isTopOrBottomHidden = (el.id === 'top' || el.id === 'bottom');
    const scrollable = isTopOrBottomHidden ? document.scrollingElement : (options.scrollable || closestScrollable(el.parentElement));
    const scrollDocument = scrollable.ownerDocument;
    const isInOneDocument = isTopOrBottomHidden || scrollDocument === el.ownerDocument;
    const iframe = !isInOneDocument && Array.from(scrollable.querySelectorAll('iframe')).find(node => node.contentDocument.contains(el));
    const topLevelScrollable = scrollDocument.scrollingElement;

    function _computeScrollTop() {
        if (el.id === 'top') {
            return 0;
        }
        if (el.id === 'bottom') {
            return scrollable.scrollHeight - scrollable.clientHeight;
        }

        let offsetTop = el.getBoundingClientRect().top + window.scrollY;
        if (el.classList.contains('d-none')) {
            el.classList.remove('d-none');
            offsetTop = el.getBoundingClientRect().top + window.scrollY;
            el.classList.add('d-none');
        }
        const isDocScrollingEl = scrollable === el.ownerDocument.scrollingElement;
        let elPosition = offsetTop - (scrollable.getBoundingClientRect().top - (isDocScrollingEl ? 0 : scrollable.scrollTop));
        if (!isInOneDocument && iframe) {
            elPosition += iframe.getBoundingClientRect().top + window.scrollY;
        }
        let offset = options.forcedOffset;
        if (offset === undefined) {
            offset = (scrollable === topLevelScrollable ? scrollFixedOffset(scrollDocument) : 0) + (options.extraOffset || 0);
        }
        return Math.max(0, elPosition - offset);
    }

    const originalScrollTop = _computeScrollTop();

    return new Promise(resolve => {
        const start = scrollable.scrollTop;
        const change = originalScrollTop - start;
        const duration = options.duration || 600;
        const startTime = performance.now();

        function animateScroll(currentTime) {
            const elapsedTime = currentTime - startTime;
            const progress = Math.min(elapsedTime / duration, 1);
            const easeInOutQuad = progress < 0.5 ? 2 * progress * progress : 1 - Math.pow(-2 * progress + 2, 2) / 2;
            const newScrollTop = start + change * easeInOutQuad;

            scrollable.scrollTop = newScrollTop;

            if (elapsedTime < duration) {
                requestAnimationFrame(animateScroll);
            } else {
                resolve();
            }
        }

        requestAnimationFrame(animateScroll);
    });
}

/**
 * Computes the size by which a scrolling point should be decreased so that
 * the top fixed elements of the page appear above that scrolling point.
 *
 * @param {Document} [doc=document]
 * @returns {number}
 */
function scrollFixedOffset(doc = document) {
    let size = 0;
    const elements = doc.querySelectorAll('.o_top_fixed_element');

    elements.forEach(el => {
        size += el.offsetHeight;
    });

    return size;
}

/**
 * Finds the closest scrollable element for the given element.
 *
 * @param {Element} element - The element to find the closest scrollable element for.
 * @returns {Element} The closest scrollable element.
 */
function closestScrollable(element) {
    const document = element.ownerDocument || window.document;

    while (element && element !== document.scrollingElement) {
        if (element instanceof Document) {
            return null;
        }
        if (isScrollable(element)) {
            return element;
        }
        element = element.parentElement;
    }
    return element || document.scrollingElement;
}

// Helper function to determine if an element is scrollable
function isScrollable(element) {
    if (!element) {
        return false;
    }
    const overflowY = window.getComputedStyle(element).overflowY;
    return overflowY === 'auto' || overflowY === 'scroll' ||
        (overflowY === 'visible' && element === element.ownerDocument.scrollingElement);
}
