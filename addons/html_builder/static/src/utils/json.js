// JSON util functions needed by the builder and by the frontend apps. This
// file must not import anything, as it is also loaded in the frontend bundle.

/**
 * Parses a JSON string without throwing if it is missing or malformed (e.g. a
 * value stored in the page HTML that was edited by hand). Use it as
 * `parseJSON(json) || fallback`.
 *
 * @param {string} [json] the JSON string to parse
 * @returns {any} the parsed value, or `undefined` if `json` is empty or is not
 * valid JSON
 */
export function parseJSON(json) {
    if (!json) {
        return;
    }
    try {
        return JSON.parse(json);
    } catch {
        return;
    }
}
