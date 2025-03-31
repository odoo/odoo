/** @odoo-module alias=@web/../tests/mobile/helpers default=false */

import { findElement, triggerEvent } from "../helpers/utils";

async function swipe(target, selector, direction) {
    const touchTarget = findElement(target, selector);
    if (direction === "left") {
        // The scrollable element is set at its right limit
        touchTarget.scrollLeft = touchTarget.scrollWidth - touchTarget.offsetWidth;
    } else {
        // The scrollable element is set at its left limit
        touchTarget.scrollLeft = 0;
    }

    await triggerEvent(target, selector, "touchstart", {
        touches: [
            {
                identifier: 0,
                clientX: 0,
                clientY: 0,
                target: touchTarget,
            },
        ],
    });
    await triggerEvent(target, selector, "touchmove", {
        touches: [
            {
                identifier: 0,
                clientX: (direction === "left" ? -1 : 1) * touchTarget.clientWidth,
                clientY: 0,
                target: touchTarget,
            },
        ],
    });
    await triggerEvent(target, selector, "touchend", {});
}

/**
 * Will simulate a swipe right on the target element with the given selector.
 *
 * @param {HTMLElement} target
 * @param {DOMSelector} [selector]
 * @returns {Promise}
 */
export async function swipeRight(target, selector) {
    return swipe(target, selector, "right");
}

/**
 * Will simulate a swipe left on the target element with the given selector.
 *
 * @param {HTMLElement} target
 * @param {DOMSelector} [selector]
 * @returns {Promise}
 */
export async function swipeLeft(target, selector) {
    return swipe(target, selector, "left");
}

/**
 * Simulate a "TAP" (touch) on the target element with the given selector.
 *
 * @param {HTMLElement} target
 * @param {DOMSelector} [selector]
 * @returns {Promise}
 */
export async function tap(target, selector) {
    const touchTarget = findElement(target, selector);
    const box = touchTarget.getBoundingClientRect();
    const x = box.left + box.width / 2;
    const y = box.top + box.height / 2;
    const touch = {
        identifier: 0,
        target: touchTarget,
        clientX: x,
        clientY: y,
        pageX: x,
        pageY: y,
    };
    await triggerEvent(touchTarget, null, "touchstart", {
        touches: [touch],
    });
    await triggerEvent(touchTarget, null, "touchend", {});
}
