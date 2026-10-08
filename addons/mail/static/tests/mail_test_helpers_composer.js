import { expect, queryFirst } from "@odoo/hoot";
import { waitUntil } from "@odoo/hoot-dom";

import { contains, insertText, TIMEOUT } from "@mail/../tests/mail_test_helpers_contains";

/**
 * @param {import("@odoo/hoot-dom").Target} selector the composer root or any element inside it
 * @returns {HTMLTextAreaElement | undefined}
 */
function findComposerInput(selector) {
    // innermost composer, e.g. the one of a message being edited
    const composerEl = queryFirst(selector)?.closest(".o-mail-Composer");
    return [...(composerEl?.querySelectorAll(".o-mail-Composer-input") ?? [])].find(
        (input) => input.closest(".o-mail-Composer") === composerEl
    );
}

/**
 * Waits for the input of the composer to be present, and returns it.
 *
 * @param {import("@odoo/hoot-dom").Target} selector the composer root or any element inside it
 * @returns {Promise<HTMLTextAreaElement>}
 */
async function waitForComposerInput(selector) {
    await contains(selector);
    return waitUntil(() => findComposerInput(selector), {
        message: `Composer input of "${selector}" not found after %timeout% milliseconds`,
        timeout: TIMEOUT,
    });
}

/**
 * @param {import("@odoo/hoot-dom").Target} selector the composer root or any element inside it
 * @param {string} text "\n" inserts a line break
 * @param {Object} [options]
 * @param {boolean} [options.replace=false] whether to clear the content first
 */
export async function insertTextInComposer(selector, text, { replace = false } = {}) {
    const input = await waitForComposerInput(selector);
    await insertText(input, text, { replace });
}

/**
 * Waits until the composer contains exactly the given text.
 *
 * @param {import("@odoo/hoot-dom").Target} selector the composer root or any element inside it
 * @param {string} text
 */
export async function containsTextInComposer(selector, text) {
    await contains(selector);
    let input;
    // The input is fetched on each check, as a re-render of the composer replaces it.
    await waitUntil(
        () => {
            input = findComposerInput(selector);
            return input?.value === text;
        },
        {
            message: () =>
                `Composer "${selector}" does not contain ${JSON.stringify(
                    text
                )} after %timeout% milliseconds (content: ${JSON.stringify(input?.value)})`,
            timeout: TIMEOUT,
        }
    );
}

/**
 * Set selection of the composer text to 'start' and 'end' values.
 *
 * @param {import("@odoo/hoot-dom").Target} selector the composer root or any element inside it
 * @param {Object} param1
 * @param {number} param1.start
 * @param {number} param1.end
 */
export async function setSelectionInComposer(selector, { start, end }) {
    const input = await waitForComposerInput(selector);
    input.setSelectionRange(start, end);
}

/**
 * Determine whether the composer text has given selection 'start' and 'end'
 *
 * @param {import("@odoo/hoot-dom").Target} selector the composer root or any element inside it
 * @param {Object} param1
 * @param {number} param1.start
 * @param {number} param1.end
 */
export async function containsSelectionInComposer(selector, { start, end }) {
    const input = await waitForComposerInput(selector);
    expect(input.selectionStart).toBe(start);
    expect(input.selectionEnd).toBe(end);
}
