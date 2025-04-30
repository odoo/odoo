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
 *
 * @typedef {[string, any[], any]} InteractionDetails
 *
 * @typedef {"interaction" | "query" | "server"} InteractionType
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
    Object: { assign: $assign },
    RegExp,
    SyntaxError,
} = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * @template {(...args: any[]) => any} T
 * @param {InteractionType} type
 * @param {T} fn
 * @param {string} name
 * @returns {T}
 */
const makeInteractorFn = (type, fn, name) =>
    ({
        [name](...args) {
            const result = fn(...args);
            if (result instanceof Promise) {
                for (let i = 0; i < args.length; i++) {
                    if (args[i] instanceof Promise) {
                        // Get promise result for async arguments if possible
                        args[i].then((result) => (args[i] = result));
                    }
                }
                return result.then((promiseResult) =>
                    dispatchInteraction(type, name, args, promiseResult)
                );
            } else {
                return dispatchInteraction(type, name, args, result);
            }
        },
    }[name]);

const DEBUG_NAMESPACE = "hoot";

const interactionBus = new EventTarget();

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * @param {Iterable<InteractionType>} types
 * @param {(event: CustomEvent<InteractionDetails>) => any} callback
 */
export function addInteractionListener(types, callback) {
    for (const type of types) {
        interactionBus.addEventListener(type, callback);
    }

    return function removeInteractionListener() {
        for (const type of types) {
            interactionBus.removeEventListener(type, callback);
        }
    };
}

/**
 * @param {InteractionType} type
 * @param {string} name
 * @param {any[]} args
 * @param {any} returnValue
 */
export function dispatchInteraction(type, name, args, returnValue) {
    interactionBus.dispatchEvent(
        new CustomEvent(type, {
            detail: [name, args, returnValue],
        })
    );
    return returnValue;
}

/**
 * @param  {...any} helpers
 */
export function exposeHelpers(...helpers) {
    let nameSpaceIndex = 1;
    let nameSpace = DEBUG_NAMESPACE;
    while (nameSpace in globalThis) {
        nameSpace = `${DEBUG_NAMESPACE}${nameSpaceIndex++}`;
    }
    globalThis[nameSpace] = new HootDebugHelpers(...helpers);
    return nameSpace;
}

/**
 * @template {(...args: any[]) => any} T
 * @param {InteractionType} type
 * @param {T} fn
 * @returns {T & {
 *  as: (name: string) => T;
 *  readonly silent: T;
 * }}
 */
export function interactor(type, fn) {
    return $assign(makeInteractorFn(type, fn, fn.name), {
        as(alias) {
            return makeInteractorFn(type, fn, alias);
        },
        get silent() {
            return fn;
        },
    });
}

/**
 * @param {Node} node
 */
export function getTag(node) {
    return node?.nodeName?.toLowerCase() || "";
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
 * @param {string} value
 * @param {{ safe?: boolean }} [options]
 * @returns {string | RegExp}
 */
export function parseRegExp(value, options) {
    const regexParams = value.match(R_REGEX);
    if (regexParams) {
        const unified = regexParams[1].replace(R_WHITE_SPACE, "\\s+");
        const flag = regexParams[2];
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

export class HootDebugHelpers {
    get $() {
        return this.queryFirst;
    }

    get $$() {
        return this.queryAll;
    }

    /**
     * @param  {...any} helpers
     */
    constructor(...helpers) {
        $assign(this, ...helpers);
    }
}

export class HootDomError extends Error {
    name = "HootDomError";
}

export const REGEX_MARKER = "/";

// Common regular expressions
export const R_REGEX = new RegExp(`^${REGEX_MARKER}(.*)${REGEX_MARKER}([dgimsuvy]+)?$`);
export const R_WHITE_SPACE = /\s+/g;
