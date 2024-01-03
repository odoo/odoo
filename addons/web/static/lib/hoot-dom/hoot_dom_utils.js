/** @odoo-module */

/**
 * @typedef {ArgumentPrimitive | `${ArgumentPrimitive}[]` | null} ArgumentType
 *
 * @typedef {"any"
 *  | "bigint"
 *  | "boolean"
 *  | "error"
 *  | "function"
 *  | "integer"
 *  | "node"
 *  | "number"
 *  | "object"
 *  | "regex"
 *  | "string"
 *  | "symbol"
 *  | "undefined"} ArgumentPrimitive
 */

/**
 * @template T
 * @typedef {T | Iterable<T>} MaybeIterable
 */

/**
 * @template T
 * @typedef {T | PromiseLike<T>} MaybePromise
 */

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const { Boolean, navigator, RegExp } = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

const R_REGEX_PATTERN = /^\/(.*)\/([dgimsuvy]+)?$/;

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * @param {Node} node
 */
export function getTag(node) {
    return node?.nodeName.toLowerCase() || "";
}

/**
 * @returns {boolean}
 */
export function isFirefox() {
    return /firefox/i.test(navigator.userAgent);
}

/**
 * Returns whether the given object is iterable (*excluding strings*).
 *
 * @template T
 * @template {T | Iterable<T>} V
 * @param {V} object
 * @returns {V extends Iterable<T> ? true : false}
 */
export function isIterable(object) {
    return Boolean(object && typeof object === "object" && object[Symbol.iterator]);
}

/**
 * @param {string} filter
 * @returns {boolean}
 */
export function isRegExpFilter(filter) {
    return R_REGEX_PATTERN.test(filter);
}

/**
 * @param {string} value
 * @returns {string | RegExp}
 */
export function parseRegExp(value) {
    const regexParams = value.match(R_REGEX_PATTERN);
    if (regexParams) {
        return new RegExp(regexParams[1].replace(/\s+/g, "\\s+"), regexParams[2] || "i");
    }
    return value;
}

/**
 * @param {Node} node
 * @param {{ raw?: boolean }} [options]
 */
export function toSelector(node, options) {
    const tagName = getTag(node);
    const id = node.id ? `#${node.id}` : "";
    const classNames = node.classList
        ? [...node.classList].map((className) => `.${className}`)
        : [];
    if (options?.raw) {
        return { tagName, id, classNames };
    } else {
        return [tagName, id, ...classNames].join("");
    }
}

export class HootDomError extends Error {
    name = "HootDomError";
}
