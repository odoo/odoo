// @ts-check
/** @odoo-module native */

/**
 * Group dictionaries and datapoint reuse must agree on identity. Preserve the
 * value type (false is not "false") and serialize dates by their value, not their
 * object identity. The resulting keys cannot collide with Object.prototype.
 * @param {any} value A parsed group value.
 * @returns {string}
 */
export function getGroupKey(value) {
    return JSON.stringify(value) ?? "undefined";
}
