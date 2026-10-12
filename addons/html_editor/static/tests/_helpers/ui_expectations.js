import { expect } from "@odoo/hoot";
import { waitFor, waitForNone } from "@odoo/hoot-dom";

/**
 * Waits for the presence or absence of elements matching the selector,
 * then asserts that the number of elements matches the expected count.
 *
 * @param {string} selector - CSS selector to query elements.
 * @param {number} count - Expected number of elements.
 */
export async function expectElementCount(selector, count) {
    if (count === 0) {
        await waitForNone(selector);
    } else {
        await waitFor(selector);
    }
    expect(selector).toHaveCount(count);
}
