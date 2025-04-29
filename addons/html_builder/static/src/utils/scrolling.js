// Scrolling util functions needed by the frontend apps and sub-modules. These
// functions indeed take into account all frontend-specific concepts (like the
// header at the top of the page, the wrapwrap,...) which are not considered in
// the `@web/core/utils/scrolling` utils.

import { getScrollingElement } from "@web/core/utils/scrolling";

/**
 * Determines if an element is scrollable.
 *
 * @param {Element} element - the element to check
 * @returns {Boolean}
 */
function isScrollable(element) {
    if (!element) {
        return false;
    }
    const overflowY = window.getComputedStyle(element).overflowY;
    return (
        overflowY === "auto" ||
        overflowY === "scroll" ||
        (overflowY === "visible" && element === element.ownerDocument.scrollingElement)
    );
}

/**
 * Finds the closest scrollable element for the given element.
 *
 * @param {Element} element - The element to find the closest scrollable element for.
 * @returns {Element} The closest scrollable element.
 */
export function closestScrollable(element) {
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

/**
 * Computes the size by which a scrolling point should be decreased so that
 * the top fixed elements of the page appear above that scrolling point.
 *
 * @param {Document} [doc=document]
 * @returns {number}
 */
function scrollFixedOffset(doc = document) {
    let size = 0;
    const elements = doc.querySelectorAll(".o_top_fixed_element");

    elements.forEach((el) => {
        size += el.offsetHeight;
    });

    return size;
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
 * @param {number} [options.duration] the scroll duration in ms
 * @return {Promise}
 */
export function scrollTo(el, options = {}) {
    if (!el) {
        throw new Error("The scrollTo function was called without any given element");
    }
    if (typeof el === "string") {
        el = document.querySelector(el);
    }
    const isTopOrBottomHidden = el === "top" || el === "bottom";
    const scrollable = isTopOrBottomHidden
        ? document.scrollingElement
        : options.scrollable || closestScrollable(el.parentElement);
    const scrollDocument = scrollable.ownerDocument;
    const isInOneDocument = isTopOrBottomHidden || scrollDocument === el.ownerDocument;
    const iframe =
        !isInOneDocument &&
        Array.from(scrollable.querySelectorAll("iframe")).find((node) =>
            node.contentDocument.contains(el)
        );
    const topLevelScrollable = getScrollingElement(scrollDocument);

    function _computeScrollTop() {
        if (el === "#top" || el.id === "top") {
            return 0;
        }
        if (el === "#bottom" || el.id === "bottom") {
            return scrollable.scrollHeight - scrollable.clientHeight;
        }

        el.classList.add("o_check_scroll_position");
        let offsetTop = el.getBoundingClientRect().top + window.scrollY;
        el.classList.remove("o_check_scroll_position");
        if (el.classList.contains("d-none")) {
            el.classList.remove("d-none");
            offsetTop = el.getBoundingClientRect().top + window.scrollY;
            el.classList.add("d-none");
        }
        const isDocScrollingEl = scrollable === el.ownerDocument.scrollingElement;
        let elPosition =
            offsetTop -
            (scrollable.getBoundingClientRect().top +
                window.scrollY -
                (isDocScrollingEl ? 0 : scrollable.scrollTop));
        if (!isInOneDocument && iframe) {
            elPosition += iframe.getBoundingClientRect().top + window.scrollY;
        }
        let offset = options.forcedOffset;
        if (offset === undefined) {
            offset =
                (scrollable === topLevelScrollable ? scrollFixedOffset(scrollDocument) : 0) +
                (options.extraOffset || 0);
        }
        return Math.max(0, elPosition - offset);
    }

    return new Promise((resolve) => {
        const start = scrollable.scrollTop;
        const duration = options.duration || 600;
        const startTime = performance.now();

        function animateScroll(currentTime) {
            const elapsedTime = currentTime - startTime;
            const progress = Math.min(elapsedTime / duration, 1);
            const easeInOutQuad =
                progress < 0.5 ? 2 * progress * progress : 1 - Math.pow(-2 * progress + 2, 2) / 2;
            // Recompute the scroll destination every time, to adapt to any
            // occurring change that would modify the scroll offset.
            const change = _computeScrollTop() - start;
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
