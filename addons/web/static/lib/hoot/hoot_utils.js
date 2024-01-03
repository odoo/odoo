/** @odoo-module */

import { isNode } from "@web/../lib/hoot-dom/helpers/dom";
import { isIterable, parseRegExp, toSelector } from "@web/../lib/hoot-dom/hoot_dom_utils";
import { DiffMatchPatch } from "./lib/diff_match_patch";

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
 * @typedef {string | RegExp | { new(): any }} Matcher
 *
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
    Array,
    clearTimeout,
    console,
    Error,
    ErrorEvent,
    JSON,
    localStorage,
    navigator,
    Object,
    Promise,
    PromiseRejectionEvent,
    Reflect,
    RegExp,
    sessionStorage,
    Set,
    setTimeout,
    String,
    TypeError,
} = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

const OBJECT_REGEX = /^\[object \w+\]$/;
const TIME_UNITS = {
    h: 60_000 * 60,
    m: 60_000,
    s: 1_000,
    ms: 0,
};

const dmp = new DiffMatchPatch();
const { DIFF_INSERT, DIFF_DELETE } = DiffMatchPatch;

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * @template P
 * @param {((...args: P[]) => any)[]} callbacks
 * @param {"pop" | "shift"} method
 * @param {...P} args
 */
export function consumeCallbackList(callbacks, method, ...args) {
    while (callbacks.length) {
        if (method === "shift") {
            callbacks.shift()(...args);
        } else {
            callbacks.pop()(...args);
        }
    }
}
/**
 * @param {string} text
 */
export async function copy(text) {
    try {
        await navigator.clipboard.writeText(text);
        console.debug(`Copied to clipboard: "${text}"`);
    } catch (err) {
        console.warn("Could not copy to clipboard:", err);
    }
}

/**
 * @template T
 * @param {T} target
 * @param {Record<string, PropertyDescriptor>} descriptors
 * @returns {T}
 */
export function createMock(target, descriptors) {
    const mock = Object.create(target);
    let owner = target;
    let keys;

    while (!keys?.length) {
        keys = Reflect.ownKeys(owner);
        owner = Object.getPrototypeOf(owner);
    }

    // Copy original descriptors
    for (const property of keys) {
        Object.defineProperty(mock, property, {
            get() {
                return target[property];
            },
            set(value) {
                target[property] = value;
            },
            configurable: true,
        });
    }

    // Apply new descriptors
    for (const [property, descriptor] of Object.entries(descriptors)) {
        Object.defineProperty(mock, property, descriptor);
    }

    return mock;
}

/**
 * @template {(...args: any[]) => any} T
 * @param {T} fn
 * @param {number} [interval]
 * @returns {T}
 */
export function batch(fn, interval) {
    /** @type {(() => ReturnType<T>)[]} */
    const currentBatch = [];
    const name = `${fn.name} (batched)`;
    let timeoutId = 0;

    return {
        [name](...args) {
            currentBatch.push(() => fn(...args));
            if (timeoutId) {
                return;
            }
            timeoutId = setTimeout(() => {
                consumeCallbackList(currentBatch, "shift");
                timeoutId = 0;
            }, interval);
        },
    }[name];
}

/**
 * @template {(...args: any[]) => any} T
 * @param {T} fn
 * @param {number} delay
 * @returns {T}
 */
export function debounce(fn, delay) {
    let timeout;
    const name = `${fn.name} (debounced)`;
    return {
        [name](...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => fn(args), delay);
        },
    }[name];
}

/**
 * @param {unknown} a
 * @param {unknown} b
 * @param {Set<unknown>} [cache=new Set()]
 * @returns {boolean}
 */
export function deepEqual(a, b, cache = new Set()) {
    if (a === b || cache.has(a)) {
        return true;
    }
    const aType = typeof a;
    if (aType !== typeof b || !a || !b) {
        return false;
    }
    if (aType === "object") {
        cache.add(a);
        if (a instanceof File) {
            return a.name === b.name && a.size === b.size && a.type === b.type;
        }
        if (isIterable(a) && isIterable(b)) {
            if (!Array.isArray(a)) {
                a = [...a];
            }
            if (!Array.isArray(b)) {
                b = [...b];
            }
            return a.length === b.length && a.every((v, i) => deepEqual(v, b[i], cache));
        }
        const aEntries = Object.entries(a);
        if (aEntries.length !== Object.keys(b).length) {
            return false;
        }
        return aEntries.every(([key, value]) => deepEqual(value, b[key], cache));
    }
    return false;
}

/**
 * @param {[unknown, ArgumentType | ArgumentType[]][]} argumentsDefs
 */
export function ensureArguments(argumentsDefs) {
    for (let i = 0; i < argumentsDefs.length; i++) {
        const [value, acceptedType] = argumentsDefs[i];
        const types = isIterable(acceptedType) ? [...acceptedType] : [acceptedType];
        if (!types.some((type) => isOfType(value, type))) {
            const strTypes = types.map(formatHumanReadable);
            const last = strTypes.pop();
            throw new TypeError(
                `expected ${ordinal(i + 1)} argument to be of type ${[strTypes.join(", "), last]
                    .filter(Boolean)
                    .join(" or ")}, got ${formatHumanReadable(value)}`
            );
        }
    }
}

/**
 * @template T
 * @param {MaybeIterable<T>} value
 * @returns {T[]}
 */
export function ensureArray(value) {
    return isIterable(value) ? [...value] : [value];
}

/**
 * @param {unknown} value
 * @returns {Error}
 */
export function ensureError(value) {
    if (value instanceof Error) {
        return value;
    }
    if (value instanceof ErrorEvent) {
        return ensureError(value.error);
    }
    if (value instanceof PromiseRejectionEvent) {
        return ensureError(value.reason);
    }
    return new Error(String(value || "unknown error"));
}

/**
 * @param {unknown} value
 * @param {{ depth?: number }} [options]
 * @returns {string}
 */
export function formatHumanReadable(value, options) {
    if (typeof value === "string") {
        if (value.length > 255) {
            value = value.slice(0, 255) + "...";
        }
        return `"${value}"`;
    } else if (typeof value === "number") {
        return value << 0 === value ? String(value) : value.toFixed(3);
    } else if (typeof value === "function") {
        const name = value.name || "anonymous";
        const prefix = /^[A-Z][a-z]/.test(name) ? `class ${name}` : `Function ${name}()`;
        return `${prefix} { ... }`;
    } else if (value && typeof value === "object") {
        if (value instanceof RegExp) {
            return value.toString();
        } else if (value instanceof Date) {
            return value.toISOString();
        } else if (isNode(value)) {
            return `<${value.nodeName.toLowerCase()}>`;
        } else if (isIterable(value)) {
            const values = [...value];
            if (values.length === 1 && isNode(values[0])) {
                // Special case for single-element nodes arrays
                return `<${values[0].nodeName.toLowerCase()}>`;
            }
            const depth = options?.depth || 0;
            const constructorPrefix =
                value.constructor.name === "Array" ? "" : `${value.constructor.name} `;
            let content = "";
            if (values.length > 1 || depth > 0) {
                content = "...";
            } else if (values.length) {
                content = formatHumanReadable(values[0], { depth: depth + 1 });
            }
            return `${constructorPrefix}[${content}]`;
        } else {
            const depth = options?.depth || 0;
            const keys = Object.keys(value);
            const constructorPrefix =
                value.constructor.name === "Object" ? "" : `${value.constructor.name} `;
            let content = "";
            if (keys.length > 1 || depth > 0) {
                content = "...";
            } else if (keys.length) {
                content = `${keys[0]}: ${formatHumanReadable(value[keys[0]], {
                    depth: depth + 1,
                })}`;
            }
            return `${constructorPrefix}{ ${content} }`;
        }
    }
    return String(value);
}

/**
 * @param {unknown} value
 * @param {Set<unknown>} [cache=new Set()]
 * @param {number} [depth=0]
 * @returns {string}
 */
export function formatTechnical(
    value,
    { cache = new Set(), depth = 0, isObjectValue = false } = {}
) {
    const baseIndent = isObjectValue ? "" : " ".repeat(depth * 2);
    if (typeof value === "string") {
        return `${baseIndent}"${value}"`;
    } else if (typeof value === "number") {
        return `${baseIndent}${value << 0 === value ? String(value) : value.toFixed(3)}`;
    } else if (typeof value === "function") {
        const name = value.name || "anonymous";
        const prefix = /^[A-Z][a-z]/.test(name) ? `class ${name}` : `Function ${name}()`;
        return `${baseIndent}${prefix} { ... }`;
    } else if (value && typeof value === "object") {
        if (cache.has(value)) {
            return `${baseIndent}${Array.isArray(value) ? "[...]" : "{ ... }"}`;
        } else {
            cache.add(value);
            const startIndent = " ".repeat((depth + 1) * 2);
            const endIndent = " ".repeat(depth * 2);
            if (value instanceof RegExp) {
                return `${baseIndent}${value.toString()}`;
            } else if (value instanceof Date) {
                return `${baseIndent}${value.toISOString()}`;
            } else if (isNode(value)) {
                return `<${toSelector(value)} />`;
            } else if (isIterable(value)) {
                const proto =
                    value.constructor.name === "Array" ? "" : `${value.constructor.name} `;
                return `${baseIndent}${proto}[\n${[...value]
                    .map(
                        (val) =>
                            `${startIndent}${formatTechnical(val, {
                                cache,
                                depth: depth + 1,
                                isObjectValue: true,
                            })},\n`
                    )
                    .join("")}${endIndent}]`;
            } else {
                const proto =
                    value.constructor.name === "Object" ? "" : `${value.constructor.name} `;
                return `${baseIndent}${proto}{\n${Object.entries(value)
                    .map(
                        ([k, v]) =>
                            `${startIndent}${k}: ${formatTechnical(v, {
                                cache,
                                depth: depth + 1,
                                isObjectValue: true,
                            })},\n`
                    )
                    .join("")}${endIndent}}`;
            }
        }
    }
    return `${baseIndent}${String(value)}`;
}

/**
 * @param {number} value
 */
export function formatTime(value) {
    for (const [unit, multiplier] of Object.entries(TIME_UNITS)) {
        if (value >= multiplier) {
            const actual = value / (multiplier || 1);
            if (actual > 10) {
                return `${actual << 0}${unit}`;
            } else {
                return `${actual.toFixed(1)}${unit}`;
            }
        }
    }
}

/**
 * Based on Java's String.hashCode, a simple but not rigorously collision resistant
 * hashing function.
 *
 * @param {...string} strings
 */
export function generateHash(...strings) {
    const str = strings.join("\x1C");

    let hash = 0;
    for (let i = 0; i < str.length; i++) {
        hash = (hash << 5) - hash + str.charCodeAt(i);
        hash |= 0;
    }

    // Convert the possibly negative number hash code into an 8 character
    // hexadecimal string
    return (hash + 16 ** 8).toString(16).slice(-8);
}

/**
 * This function computes a score that represent the fact that the
 * string contains the pattern, or not
 *
 * - If the score is 0, the string does not contain the letters of the pattern in
 *   the correct order.
 * - if the score is > 0, it actually contains the letters.
 *
 * Better matches will get a higher score: consecutive letters are better,
 * and a match closer to the beginning of the string is also scored higher.
 *
 * @param {string} pattern (normalized)
 * @param {string} string (normalized)
 */
export function getFuzzyScore(pattern, string) {
    let totalScore = 0;
    let currentScore = 0;
    let patternIndex = 0;

    const length = string.length;
    for (let i = 0; i < length; i++) {
        if (string[i] === pattern[patternIndex]) {
            patternIndex++;
            currentScore += 100 + currentScore - i / 200;
        } else {
            currentScore = 0;
        }
        totalScore = totalScore + currentScore;
    }

    return patternIndex === pattern.length ? totalScore : 0;
}

/**
 * @param  {...unknown} args
 */
export function hootLog(...args) {
    const prefix = `%c[HOOT]%c`;
    const styles = [`color:#ff0080`, `color:inherit`];
    const firstArg = args.shift() ?? "";
    if (typeof firstArg === "string") {
        args.unshift(`${prefix} ${firstArg}`, ...styles);
    } else {
        args.unshift(prefix, ...styles, firstArg);
    }
    return args;
}

/**
 * Returns whether the given value is either `null` or `undefined`.
 *
 * @template T
 * @param {T} value
 * @returns {T extends (undefined | null) ? true : false}
 */
export function isNil(value) {
    return value === null || value === undefined;
}

/**
 * @param {unknown} value
 * @param {ArgumentType} type
 * @returns {boolean}
 */
export function isOfType(value, type) {
    if (typeof type === "string" && type.endsWith("[]")) {
        const itemType = type.slice(0, -2);
        return isIterable(value) && [...value].every((v) => isOfType(v, itemType));
    }
    switch (type) {
        case null:
        case undefined:
            return value === null || value === undefined;
        case "any":
            return true;
        case "error":
            return value instanceof Error;
        case "integer":
            return Number.isInteger(value);
        case "node":
            return isNode(value);
        case "regex":
            return value instanceof RegExp;
        default:
            return typeof value === type;
    }
}

export function toExplicitString(value) {
    const strValue = String(value);
    switch (strValue) {
        case "\n":
            return "\\n";
        case "\t":
            return "\\t";
    }
    return strValue;
}

/**
 * Returns a list of items that match the given pattern, ordered by their 'score'
 * (descending). A higher score means that the match is closer (e.g. consecutive
 * letters).
 *
 * @template T
 * @param {string} pattern
 * @param {Iterable<T>} items
 * @param {(item: T) => string} mapFn
 * @returns {T[]}
 */
export function lookup(pattern, items, mapFn = normalize) {
    const nPattern = parseRegExp(normalize(pattern));
    if (nPattern instanceof RegExp) {
        return [...items].filter((item) => nPattern.test(mapFn(item)));
    } else {
        // Fuzzy lookup
        const result = [];
        for (const item of items) {
            const score = getFuzzyScore(nPattern, mapFn(item));
            if (score > 0) {
                result.push([item, score]);
            }
        }
        return result.sort((a, b) => b[1] - a[1]).map(([item]) => item);
    }
}

export function makeCallbacks() {
    /**
     * @template P
     * @param {string} type
     * @param {MaybePromise<(...args: P[]) => MaybePromise<((...args: P[]) => void) | void>>} callback
     * @param {boolean} [once]
     */
    const add = (type, callback, once) => {
        if (callback instanceof Promise) {
            callback = () =>
                Promise.resolve(callback).then((result) => {
                    if (typeof result === "function") {
                        result();
                    }
                });
        }
        if (typeof callback !== "function") {
            return;
        }
        if (!callbackRegistry[type]) {
            callbackRegistry[type] = new Set();
        }
        if (once) {
            const originalCallback = callback;
            callback = (...args) => {
                const result = originalCallback(...args);
                remove(type, callback);
                return result;
            };
        }
        callbackRegistry[type].add(callback);
    };

    /**
     * @param {string} type
     * @param {...any} args
     */
    const call = async (type, ...args) => {
        if (!callbackRegistry[type]) {
            return;
        }
        const fns = [...callbackRegistry[type]];
        if (type.startsWith("after")) {
            fns.reverse();
        }
        const results = await Promise.all(
            fns.map((fn) => Promise.resolve(fn(...args)).catch(console.error))
        );
        if (type.startsWith("before")) {
            const relatedType = `after${type.slice(6)}`;
            for (const relatedCallback of results) {
                if (relatedCallback) {
                    add(relatedType, relatedCallback, true);
                }
            }
        }
    };

    /**
     * @param {string} type
     * @param {(...args: any[]) => MaybePromise<void>} callback
     */
    const remove = (type, callback) => {
        if (!callbackRegistry[type]) {
            return;
        }
        callbackRegistry[type].delete(callback);
    };

    /** @type {Record<string, Set<(...args: any[]) => MaybePromise<((...args: any[]) => void) | void>>>} */
    const callbackRegistry = {};

    return { add, call, remove };
}

/**
 * @param {EventTarget} target
 * @param {string[]} types
 */
export function makePublicListeners(target, types) {
    for (const type of types) {
        let listener = null;
        Object.defineProperty(target, `on${type}`, {
            get() {
                return listener;
            },
            set(value) {
                listener = value;
            },
        });
        target.addEventListener(type, (...args) => listener?.(...args));
    }
}

/**
 * Returns whether one of the given `matchers` matches the given `value`.
 *
 * @param {unknown} value
 * @param {...Matcher} matchers
 * @returns {boolean}
 */
export function match(value, ...matchers) {
    if (!matchers.length) {
        return !value;
    }
    for (let matcher of matchers) {
        if (typeof matcher === "function") {
            matcher = new RegExp(matcher.name);
        } else if (typeof matcher === "string") {
            matcher = new RegExp(matcher, "i");
        }
        let strValue = String(value);
        if (OBJECT_REGEX.test(strValue)) {
            strValue = value.constructor.name;
        }
        if (matcher.test(strValue)) {
            return true;
        }
    }
    return false;
}

/**
 * @param {string} string
 * @returns {string}
 */
export function normalize(string) {
    return string
        .trim()
        .toLowerCase()
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "");
}

export async function paste() {
    try {
        await navigator.clipboard.readText();
    } catch (err) {
        console.warn("Could not paste from clipboard:", err);
    }
}

/**
 * @param {"local" | "session"} type
 */
export function storage(type) {
    /**
     * @template T
     * @param {string} key
     * @param {T} defaultValue
     * @returns {T}
     */
    const get = (key, defaultValue) => {
        const value = s.getItem(`hoot-${key}`);
        return value ? JSON.parse(value) : defaultValue;
    };

    /**
     * @param  {...string} keys
     */
    const remove = (...keys) => {
        for (const key of keys) {
            s.removeItem(`hoot-${key}`);
        }
    };

    /**
     * @template T
     * @param {string} key
     * @param {T} value
     */
    const set = (key, value) => s.setItem(`hoot-${key}`, JSON.stringify(value));

    const s = type === "local" ? localStorage : sessionStorage;

    return { get, remove, set };
}

/**
 * @param {string} string
 */
export function stringToNumber(string) {
    let result = "";
    for (let i = 0; i < string.length; i++) {
        result += string.charCodeAt(i);
    }
    return Number(result);
}

/**
 * @param {string} string
 */
export function title(string) {
    return string[0].toUpperCase() + string.slice(1);
}

export class HootError extends Error {
    name = "HootError";
}

export class Markup {
    /**
     * @param {{
     *  className?: string;
     *  content: any;
     *  tagName?: string;
     *  technical?: boolean;
     * }} params
     */
    constructor(params) {
        this.className = params.className || "";
        this.tagName = params.tagName || "div";
        this.content = params.content || "";
        this.technical = params.technical;
    }

    /**
     * @param {unknown} a
     * @param {unknown} b
     */
    static diff(a, b) {
        return new this({
            technical: true,
            content: dmp.diff_main(formatTechnical(a), formatTechnical(b)).map((diff) => {
                let tagName = "t";
                if (diff[0] === DIFF_INSERT) {
                    tagName = "ins";
                } else if (diff[0] === DIFF_DELETE) {
                    tagName = "del";
                }
                return new this({ content: toExplicitString(diff[1]), tagName });
            }),
        });
    }

    /** @param {string} content */
    static green(content) {
        return new this({ className: "hoot-text-pass", content });
    }

    /** @param {string} content */
    static red(content) {
        return new this({ className: "hoot-text-fail", content });
    }

    /**
     * @param {string} content
     * @param {{ technical?: boolean }} [options]
     */
    static text(content, options) {
        return new this({ ...options, content });
    }
}
