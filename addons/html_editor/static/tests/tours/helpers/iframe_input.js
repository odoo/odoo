/**
 * Waits for an `<input>` inside an iframe anchor to have a value, then returns it.
 *
 * @param {HTMLIFrameElement} anchor - The iframe element (`this.anchor` in tour steps).
 * @param {string} inputSelector - CSS selector for the input inside the iframe.
 * @param {function} waitUntil - `waitUntil` from the tour runner's `run({ waitUntil })`.
 * @returns {Promise<HTMLInputElement>}
 */
export async function getIframeInput(anchor, inputSelector, waitUntil) {
    return waitUntil(() => {
        const input = anchor?.contentWindow?.document?.querySelector(inputSelector);
        return input?.value && input;
    });
}

/**
 * Waits for an `<input>` inside an iframe anchor to have a value, sets a new
 * value on it, and dispatches an event.
 *
 * @param {HTMLIFrameElement} anchor - The iframe element (`this.anchor` in tour steps).
 * @param {string} inputSelector - CSS selector for the input inside the iframe.
 * @param {string|number} value - The value to set on the input.
 * @param {function} waitUntil - `waitUntil` from the tour runner's `run({ waitUntil })`.
 * @param {Object} [options]
 * @param {string} [options.eventType="change"] - Event dispatched after the value is set.
 * @returns {Promise<HTMLInputElement>}
 */
export async function setIframeInput(
    anchor,
    inputSelector,
    value,
    waitUntil,
    { eventType = "change" } = {}
) {
    const input = await getIframeInput(anchor, inputSelector, waitUntil);
    input.value = value;
    input.dispatchEvent(new Event(eventType));
    return input;
}
