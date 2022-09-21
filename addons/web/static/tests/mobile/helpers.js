/** @odoo-module **/

import { triggerEvent } from "../helpers/utils";

async function swipe(target, selector, direction) {
    const touchTarget = target.querySelector(selector);
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

export function swipeRight(target, selector) {
    return swipe(target, selector, "right");
}

export function swipeLeft(target, selector) {
    return swipe(target, selector, "left");
}
