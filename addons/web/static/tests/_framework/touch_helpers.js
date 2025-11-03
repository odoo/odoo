import { advanceTime, queryFirst } from "@odoo/hoot";
import { contains } from "./dom_test_helpers";

/**
 * @typedef {import("@odoo/hoot").PointerOptions} PointerOptions
 * @typedef {import("@odoo/hoot").Target} Target
 */

/**
 * @param {Target} target
 * @param {number} direction
 * @param {PointerOptions} [dragOptions]
 * @param {PointerOptions} [moveToOptions]
 * @returns {Promise<void>}
 */
async function swipe(target, direction, dragOptions, moveToOptions) {
    const el = queryFirst(target);
    if (direction < 0) {
        // The scrollable element is set at its right limit
        el.scrollLeft = el.scrollWidth - el.offsetWidth;
    } else {
        // The scrollable element is set at its left limit
        el.scrollLeft = 0;
    }

    const { moveTo, drop } = await contains(el).drag({
        position: { x: 0, y: 0 },
        ...dragOptions,
    });

    await moveTo(el, {
        position: { x: direction * el.clientWidth },
        ...moveToOptions,
    });

    await drop();
    await advanceTime(1000);
}

/**
 * Will simulate a swipe left on the target element.
 *
 * @param {Target} target
 * @param {PointerOptions} [dragOptions]
 * @param {PointerOptions} [moveToOptions]
 * @returns {Promise<void>}
 */
export async function swipeLeft(target, dragOptions, moveToOptions) {
    await swipe(target, -1, dragOptions, moveToOptions);
}

/**
 * Will simulate a swipe right on the target element.
 *
 * @param {Target} target
 * @param {PointerOptions} [dragOptions]
 * @param {PointerOptions} [moveToOptions]
 * @returns {Promise<void>}
 */
export async function swipeRight(target, dragOptions, moveToOptions) {
    await swipe(target, +1, dragOptions, moveToOptions);
}
