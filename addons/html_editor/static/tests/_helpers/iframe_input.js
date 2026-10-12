import { queryOne, waitUntil } from "@odoo/hoot-dom";

/**
 * Waits for and returns an `<input>` inside an iframe once it has a value.
 *
 * @param {string} iframeSelector - CSS selector for the iframe element.
 * @param {string} inputSelector - CSS selector for the input inside the iframe.
 * @returns {Promise<HTMLInputElement>}
 */
export async function getIframeInput(iframeSelector, inputSelector) {
    return waitUntil(() => {
        const iframeEl = queryOne(iframeSelector);
        const input = iframeEl?.contentWindow?.document?.querySelector(inputSelector);
        return input?.value && input;
    });
}
