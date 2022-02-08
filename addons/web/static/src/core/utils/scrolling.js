/** @odoo-module */

/**
 * Ensures that `element` will be visible in its `scrollable`.
 *
 * @param {HTMLElement} element
 * @param {Object} options
 * @param {HTMLElement} options[scrollable] a scrollable area
 * @param {Boolean} options[isAnchor] states if the scroll is to an anchor
 */
export function scrollTo(element, options = { scrollable: null, isAnchor: false }) {
    function _getScrollParent(node) {
        if (node == null) {
            return null;
        }

        if (node.scrollHeight > node.clientHeight && node.clientHeight > 0) {
            return node;
        } else {
            return _getScrollParent(node.parentNode);
        }
    }

    const scrollable = options.scrollable
        ? options.scrollable
        : _getScrollParent(element.parentNode);
    if (scrollable) {
        const scrollBottom = scrollable.getBoundingClientRect().bottom;
        const scrollTop = scrollable.getBoundingClientRect().top;
        const elementBottom = element.getBoundingClientRect().bottom;
        const elementTop = element.getBoundingClientRect().top;
        if (elementBottom > scrollBottom && !options.isAnchor) {
            // The scroll place the element at the bottom border of the scrollable
            scrollable.scrollTop +=
                elementTop - scrollBottom + element.getBoundingClientRect().height;
        } else if (elementTop < scrollTop || options.isAnchor) {
            // The scroll place the element at the top of the scrollable
            scrollable.scrollTop -= scrollTop - elementTop;
            if (options.isAnchor) {
                // If the scrollable is within a scrollable, another scroll should be done
                const parentScrollable = _getScrollParent(scrollable.parentNode);
                if (parentScrollable) {
                    scrollTo(scrollable, { isAnchor: true, scrollable: parentScrollable });
                }
            }
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
