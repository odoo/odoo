/** @odoo-module **/

/*
 * Returns the main scrollable element relevant in a context of an action.
 * In desktop, the relevant element is the .o_content of the action.
 * In mobile, it is the html node itself, provided no other children is scrollable
 *   Most of the times in mobile, we don't want to scroll individual elements, so every bit
 *   of code should enforce that html is the scrollable element.
 *
 * @param {OdooEnv} env
 * @return {Element}
 */
function getScrollableElement(env) {
    if (env.isSmall) {
        return document.firstElementChild; // aka html node;
    } else {
        return document.querySelector(".o_web_client > .o_action_manager > .o_action > .o_content");
    }
}

/**
 * Retrieves the current top and left scroll position. By default, the scrolling
 * area is the '.o_content' main div. In mobile, it is the body.
 *
 * @param {OdooEnv} env
 */
export function getScrollPosition(env) {
    const scrollingEl = getScrollableElement(env);
    return {
        left: scrollingEl ? scrollingEl.scrollLeft : 0,
        top: scrollingEl ? scrollingEl.scrollTop : 0,
    };
}

/**
 * Sets top and left scroll positions to the given values. By default, the
 * scrolling area is the '.o_content' main div. In mobile, it is the body.
 *
 * @param {OdooEnv} env
 * @param {Object} offset
 * @param {number} [offset.left=0]
 * @param {number} [offset.top=0]
 */
export function setScrollPosition(env, offset) {
    const scrollingEl = getScrollableElement(env);
    if (scrollingEl) {
        scrollingEl.scrollLeft = offset.left || 0;
        scrollingEl.scrollTop = offset.top || 0;
    }
}
