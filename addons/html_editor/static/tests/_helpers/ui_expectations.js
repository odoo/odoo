import { expect } from "@odoo/hoot";
import { waitFor, waitForNone } from "@odoo/hoot-dom";

/**
 * Waits for the presence or absence of elements matching the selector,
 * then asserts that the number of elements matches the expected count.
 *
 * @param {string} selector - CSS selector to query elements.
 * @param {number} count - Expected number of elements.
 * @param {{ timeout?: number }} [options] - Options passed to the wait helper.
 */
export async function expectElementCount(selector, count, options) {
    if (count === 0) {
        await waitForNone(selector, options);
    } else {
        await waitFor(selector, options);
    }
    expect(selector).toHaveCount(count);
}
