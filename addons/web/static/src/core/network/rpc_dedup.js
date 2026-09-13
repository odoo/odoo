// @ts-check
/** @odoo-module native */

/**
 * @param {any} value
 * @returns {string | undefined}
 */
export function stableStringify(value) {
    const serialized = JSON.stringify(value);
    return serialized === undefined
        ? undefined
        : stringifyOrdered(JSON.parse(serialized));
}

/** @param {any} value @returns {string} */
function stringifyOrdered(value) {
    if (value === null || typeof value !== "object") {
        return JSON.stringify(value);
    }
    if (Array.isArray(value)) {
        return `[${value.map(stringifyOrdered).join(",")}]`;
    }
    const parts = [];
    for (const key of Object.keys(value).sort()) {
        parts.push(`${JSON.stringify(key)}:${stringifyOrdered(value[key])}`);
    }
    return `{${parts.join(",")}}`;
}

/**
 * @param {string} url
 * @param {any} params
 * @returns {string}
 */
export function getKey(url, params) {
    return /** @type {string} */ (stableStringify({ url, params }));
}
