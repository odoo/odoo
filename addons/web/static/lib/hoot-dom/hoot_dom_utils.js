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

const {
    Boolean,
    navigator: { userAgent: $userAgent },
    RegExp,
    SyntaxError,
} = globalThis;

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
    return /firefox/i.test($userAgent);
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
 * @param {{ safe?: boolean }} [options]
 * @returns {string | RegExp}
 */
export function parseRegExp(value, options) {
    const regexParams = value.match(R_REGEX_PATTERN);
    if (regexParams) {
        const unified = regexParams[1].replace(/\s+/g, "\\s+");
        const flag = regexParams[2] || "i";
        try {
            return new RegExp(unified, flag);
        } catch (error) {
            if (error instanceof SyntaxError && options?.safe) {
                return value;
            } else {
                throw error;
            }
        }
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
