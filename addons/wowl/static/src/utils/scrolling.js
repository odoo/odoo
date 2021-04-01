/** @odoo-module */

/**
 * Ensures that `element` will be visible in its `scrollable`.
 *
 * @param {HTMLElement} element
 * @param {HTMLElement} scrollable
 */
export function scrollTo(element, scrollable) {
  // Scrollbar is present ?
  if (scrollable.scrollHeight > scrollable.clientHeight) {
    const scrollBottom = scrollable.clientHeight + scrollable.scrollTop;
    const elementBottom = element.offsetTop + element.offsetHeight;
    if (elementBottom > scrollBottom) {
      // Scroll down
      scrollable.scrollTop = elementBottom - scrollable.clientHeight;
    } else if (element.offsetTop < scrollable.scrollTop) {
      // Scroll up
      scrollable.scrollTop = element.offsetTop;
    }
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
  let scrollingEl;
  if (component.env.isSmall) {
    scrollingEl = document.body;
  } else {
    scrollingEl = component.el.querySelector(".o_action_manager .o_content");
  }
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
  let scrollingEl;
  if (component.env.isSmall) {
    scrollingEl = document.body;
  } else {
    scrollingEl = component.el.querySelector(".o_action_manager .o_content");
  }
  if (scrollingEl) {
    scrollingEl.scrollLeft = offset.left || 0;
    scrollingEl.scrollTop = offset.top || 0;
  }
}
