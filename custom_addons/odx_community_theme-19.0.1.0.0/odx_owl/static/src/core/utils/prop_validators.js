/** @odoo-module **/

/**
 * Reusable prop validators for ODX OWL components.
 *
 * OWL's prop system doesn't support union types (String | Number | null).
 * These validators provide safety where `validate: () => true` is too loose.
 */

/**
 * Value can be a string, number, boolean, null, undefined, or Date.
 * Rejects functions (common mistake: passing callback instead of value).
 */
export function isScalarValue(v) {
    return v === null || v === undefined || typeof v !== "function" && typeof v !== "symbol";
}

/**
 * Must be a plain object (config, settings) or null/undefined.
 * Rejects arrays, functions, and other non-object types.
 */
export function isObjectOrEmpty(v) {
    if (v === null || v === undefined) return true;
    return typeof v === "object" && !Array.isArray(v);
}

/**
 * Must be an array or null/undefined.
 */
export function isArrayOrEmpty(v) {
    return v === null || v === undefined || Array.isArray(v);
}

/**
 * Sort config: { key: string, direction: "asc"|"desc" } or null.
 */
export function isSortConfig(v) {
    if (v === null || v === undefined) return true;
    return typeof v === "object" && !Array.isArray(v)
        && (typeof v.key === "string" || v.key === undefined);
}

/**
 * Chart series: array of objects with { key, label?, color?, ... } or strings.
 */
export function isChartSeries(v) {
    if (v === null || v === undefined) return true;
    return Array.isArray(v);
}
