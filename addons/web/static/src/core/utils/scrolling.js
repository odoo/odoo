/** @odoo-module */

/**
 * Ensures that `element` will be visible in its `scrollable`.
 *
 * @param {HTMLElement} element
 * @param {HTMLElement} [scrollable]
 */
export function scrollTo(element, scrollable = null) {
    function _getScrollParent(node) {
        if (node == null) {
            return null;
        }

        if (node.scrollHeight > node.clientHeight) {
            return node;
        } else {
            return _getScrollParent(node.parentNode);
        }
    }
    scrollable = scrollable ? scrollable : _getScrollParent(element);

    // Scrollbar is present ?
    if (scrollable.scrollHeight > scrollable.clientHeight) {
        const scrollBottom = scrollable.getBoundingClientRect().bottom;
        const elementBottom = element.getBoundingClientRect().bottom;
        if (elementBottom > scrollBottom) {
            // Scroll down
            scrollable.scrollTop = elementBottom - scrollable.getBoundingClientRect().height;
        } else if (element.getBoundingClientRect().top < scrollable.getBoundingClientRect().top) {
            // Scroll up
            scrollable.scrollTop = element.getBoundingClientRect().top;
        }
    }
}

/*
 * Returns the main scrollable element relevant in a context of an action.
 * In desktop, the relevant element is the .o_content of the action.
 * In mobile, it is the html node itself, provided no other children is scrollable
 *   Most of the times in mobile, we don't want to scroll individual elements, so every bit
 *   of code should enforce that html is the scrollable element.
 *
 * @param {Component} The action component.
 * @return {Element}
 */
function getScrollableElement(component) {
    if (component.env.isSmall) {
        return document.firstElementChild; // aka html node;
    } else {
        return component.el.querySelector(".o_action_manager .o_content");
    }
}

/**
 * Retrieves the current top and left scroll position. By default, the scrolling
 * area is the '.o_content' main div. In mobile, it is the body.
 *
 * @param {Component} an action Component containing an .o_content scrollable
 *   area.
 */
export function getScrollPosition(component) {
    const scrollingEl = getScrollableElement(component);
    return {
        left: scrollingEl ? scrollingEl.scrollLeft : 0,
        top: scrollingEl ? scrollingEl.scrollTop : 0,
    };
}

/**
 * Sets top and left scroll positions to the given values. By default, the
 * scrolling area is the '.o_content' main div. In mobile, it is the body.
 *
 * @param {Component} an action Component containing an .o_content scrollable
 *   area.
 * @param {Object} offset
 * @param {number} [offset.left=0]
 * @param {number} [offset.top=0]
 */
export function setScrollPosition(component, offset) {
    const scrollingEl = getScrollableElement(component);
    if (scrollingEl) {
        scrollingEl.scrollLeft = offset.left || 0;
        scrollingEl.scrollTop = offset.top || 0;
    }
}
