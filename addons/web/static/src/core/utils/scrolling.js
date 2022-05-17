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

/**
 * Returns the scrollLeft and scrollTop properties of the given element.
 *
 * @param {Element} el
 * @returns {Object} with keys "left" and "top"
 */
export function getScrollPosition(el) {
    return { left: el.scrollLeft, top: el.scrollTop };
}

/**
 * Sets the scrollLeft and scrollTop properties on the given element.
 *
 * @param {Element} el
 * @param {Object} offset
 * @param {number} [offset.left=0]
 * @param {number} [offset.top=0]
 */
export function setScrollPosition(el, offset) {
    el.scrollLeft = offset.left || 0;
    el.scrollTop = offset.top || 0;
}
