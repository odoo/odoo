/** @odoo-module */

import { reactive, useExternalListener } from "@odoo/owl";
import { isNode } from "@web/../lib/hoot-dom/helpers/dom";
import { isIterable, toSelector } from "@web/../lib/hoot-dom/hoot_dom_utils";
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
 * @typedef {{
 *  assertions: number;
 *  failed: number;
 *  passed: number;
 *  skipped: number;
 *  suites: number;
 *  tests: number;
 *  todo: number;
 * }} Reporting
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
    console: { debug: $debug },
    Date,
    Error,
    ErrorEvent,
    Map,
    Math: { floor },
    Number: { isInteger: $isInteger, isNaN: $isNaN, parseFloat: $parseFloat },
    navigator: { clipboard: $clipboard },
    Object: {
        assign: $assign,
        create: $create,
        defineProperty: $defineProperty,
        entries: $entries,
        getPrototypeOf: $getPrototypeOf,
        keys: $keys,
    },
    Promise,
    PromiseRejectionEvent,
    Reflect: { ownKeys },
    RegExp,
    Set,
    setTimeout,
    String,
    TypeError,
    window,
} = globalThis;
/** @type {Clipboard["readText"]} */
const $readText = $clipboard.readText.bind($clipboard);
/** @type {Clipboard["writeText"]} */
const $writeText = $clipboard.writeText.bind($clipboard);

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * @param {unknown} number
 */
const ordinal = (number) => {
    const strNumber = String(number);
    if (strNumber.at(-2) === "1") {
        return `${strNumber}th`;
    }
    switch (strNumber.at(-1)) {
        case "1": {
            return `${strNumber}st`;
        }
        case "2": {
            return `${strNumber}nd`;
        }
        case "3": {
            return `${strNumber}rd`;
        }
        default: {
            return `${strNumber}th`;
        }
    }
};

const R_OBJECT = /^\[object \w+\]$/;

const dmp = new DiffMatchPatch();
const { DIFF_INSERT, DIFF_DELETE } = DiffMatchPatch;

const windowTarget = {
    addEventListener: window.addEventListener.bind(window),
    removeEventListener: window.removeEventListener.bind(window),
};

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
        await $writeText(text);
        $debug(`Copied to clipboard: "${text}"`);
    } catch (err) {
        console.warn("Could not copy to clipboard:", err);
    }
}

/**
 * @param {Reporting} [parentReporting]
 */
export function createReporting(parentReporting) {
    /**
     * @param {Partial<Reporting>} values
     */
    const add = (values) => {
        for (const [key, value] of $entries(values)) {
            reporting[key] += value;
        }

        parentReporting?.add(values);
    };

    const reporting = reactive({
        assertions: 0,
        failed: 0,
        passed: 0,
        skipped: 0,
        suites: 0,
        tests: 0,
        todo: 0,
        add,
    });

    return reporting;
}

/**
 * @template T
 * @param {T} target
 * @param {Record<string, PropertyDescriptor>} descriptors
 * @returns {T}
 */
export function createMock(target, descriptors) {
    const mock = $create(target);
    let owner = target;
    let keys;

    while (!keys?.length) {
        keys = ownKeys(owner);
        owner = $getPrototypeOf(owner);
    }

    // Copy original descriptors
    for (const property of keys) {
        $defineProperty(mock, property, {
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
    for (const [property, descriptor] of $entries(descriptors)) {
        $defineProperty(mock, property, descriptor);
    }

    return mock;
}

/**
 * @template {(...args: any[]) => any} T
 * @param {T} fn
 * @param {number} [interval]
 */
export function batch(fn, interval) {
    /** @type {(() => ReturnType<T>)[]} */
    const currentBatch = [];
    let timeoutId = 0;

    /** @type {T} */
    const batched = (...args) => {
        currentBatch.push(() => fn(...args));
        if (timeoutId) {
            return;
        }
        timeoutId = setTimeout(() => {
            timeoutId = 0;
            flush();
        }, interval);
    };

    const flush = () => {
        if (timeoutId) {
            clearTimeout(timeoutId);
            timeoutId = 0;
        }
        consumeCallbackList(currentBatch, "shift");
    };

    return [batched, flush];
}

/**
 * @template {(...args: any[]) => any} T
 * @param {T} fn
 * @param {number} delay
 * @returns {T}
 */
export function debounce(fn, delay) {
    let timeout = 0;
    const name = `${fn.name} (debounced)`;
    return {
        [name](...args) {
            if (timeout) {
                clearTimeout(timeout);
            }
            timeout = setTimeout(() => {
                timeout = 0;
                fn(args);
            }, delay);
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
    if (strictEqual(a, b) || cache.has(a)) {
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
        const aEntries = $entries(a);
        if (aEntries.length !== $keys(b).length) {
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
            const keys = $keys(value);
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
                return `${baseIndent}${proto}{\n${$entries(value)
                    .sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))
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
 * @param {"ms" | "s"} [unit]
 */
export function formatTime(value, unit) {
    value ||= 0;
    if (unit) {
        if (unit === "s") {
            value /= 1_000;
        }
        if (value < 10) {
            value = $parseFloat(value.toFixed(3));
        } else if (value < 100) {
            value = $parseFloat(value.toFixed(2));
        } else if (value < 1_000) {
            value = $parseFloat(value.toFixed(1));
        } else {
            const str = String(floor(value));
            return `${str.slice(0, -3) + "," + str.slice(-3)}${unit}`;
        }
        return value + unit;
    }

    value = floor(value / 1_000);

    const seconds = value % 60;
    value -= seconds;

    const minutes = (value / 60) % 60;
    value -= minutes * 60;

    const hours = value / 3_600;

    return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(
        seconds
    ).padStart(2, "0")}`;
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
            return $isInteger(value);
        case "node":
            return isNode(value);
        case "regex":
            return value instanceof RegExp;
        default:
            return typeof value === type;
    }
}

/**
 * @param {unknown} value
 */
export function toExplicitString(value) {
    const strValue = String(value);
    switch (strValue) {
        case "\n":
            return "\\n";
        case "\t":
            return "\\t";
    }
    // replace zero-width spaces with their explicit representation
    return strValue.replace(
        /[\u200B-\u200D\uFEFF]/g,
        (char) => `\\u${char.charCodeAt(0).toString(16).padStart(4, "0")}`
    );
}

/**
 * Returns a list of items that match the given pattern, ordered by their 'score'
 * (descending). A higher score means that the match is closer (e.g. consecutive
 * letters).
 *
 * @template T
 * @param {string | RegExp} pattern normalized string or RegExp
 * @param {Iterable<T>} items
 * @param {(item: T) => string} mapFn
 * @returns {T[]}
 */
export function lookup(pattern, items, mapFn = normalize) {
    if (pattern instanceof RegExp) {
        return [...items].filter((item) => pattern.test(mapFn(item)));
    } else {
        // Fuzzy lookup
        const result = [];
        for (const item of items) {
            const score = getFuzzyScore(pattern, mapFn(item));
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
    const addCallback = (type, callback, once) => {
        if (callback instanceof Promise) {
            callback = () =>
                Promise.resolve(callback).then((result) => {
                    if (typeof result === "function") {
                        result();
                    }
                });
        } else if (typeof callback !== "function") {
            return;
        }

        if (once) {
            // Convert callback to be automatically removed
            const originalCallback = callback;
            callback = (...args) => {
                callbackMap.set(
                    type,
                    callbackMap.get(type).filter((fn) => fn !== callback)
                );
                return originalCallback(...args);
            };
            $assign(callback, { original: originalCallback });
        }

        if (!callbackMap.has(type)) {
            callbackMap.set(type, []);
        }
        if (type.startsWith("after")) {
            callbackMap.get(type).unshift(callback);
        } else {
            callbackMap.get(type).push(callback);
        }
    };

    /**
     * @param {string} type
     * @param {...any} args
     */
    const call = async (type, ...args) => {
        const fns = callbackMap.get(type);
        if (!fns?.length) {
            return;
        }

        const afterCallback = getAfterCallback(type);
        for (const fn of fns) {
            await Promise.resolve(fn(...args)).then(afterCallback, console.error);
        }
    };

    /**
     * @param {string} type
     * @param {...any} args
     */
    const callSync = (type, ...args) => {
        const fns = callbackMap.get(type);
        if (!fns?.length) {
            return;
        }

        const afterCallback = getAfterCallback(type);
        for (const fn of fns) {
            try {
                const result = fn(...args);
                afterCallback(result);
            } catch (err) {
                console.error(err);
            }
        }
    };

    const clearCallbacks = () => {
        callbackMap.clear();
    };

    /**
     * @param {string} type
     */
    const getAfterCallback = (type) => {
        if (!type.startsWith("before")) {
            return () => {};
        }
        const relatedType = `after${type.slice(6)}`;
        return (result) => addCallback(relatedType, result, true);
    };

    /** @type {Map<string, ((...args: any[]) => MaybePromise<((...args: any[]) => void) | void>)[]>} */
    const callbackMap = new Map();

    return { add: addCallback, call, callSync, clear: clearCallbacks };
}

/**
 * @param {EventTarget} target
 * @param {string[]} types
 */
export function makePublicListeners(target, types) {
    for (const type of types) {
        let listener = null;
        $defineProperty(target, `on${type}`, {
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
    return matchers.some((matcher) => {
        if (typeof matcher === "function") {
            if (value instanceof matcher) {
                return true;
            }
            matcher = new RegExp(matcher.name);
        }
        let strValue = String(value);
        if (R_OBJECT.test(strValue)) {
            strValue = value.constructor.name;
        }
        if (matcher instanceof RegExp) {
            return matcher.test(strValue);
        } else {
            return strValue.includes(String(matcher));
        }
    });
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
        await $readText();
    } catch (err) {
        console.warn("Could not paste from clipboard:", err);
    }
}

/**
 * @param {unknown} a
 * @param {unknown} b
 * @returns {boolean}
 */
export function strictEqual(a, b) {
    return $isNaN(a) ? $isNaN(b) : a === b;
}

/**
 * @param {string} string
 */
export function stringToNumber(string) {
    let result = "";
    for (let i = 0; i < string.length; i++) {
        result += string.charCodeAt(i);
    }
    return $parseFloat(result);
}

/**
 * @param {string} string
 */
export function title(string) {
    return string[0].toUpperCase() + string.slice(1);
}

/** @type {EventTarget["addEventListener"]} */
export function useWindowListener(type, callback, options) {
    return useExternalListener(windowTarget, type, (ev) => ev.isTrusted && callback(ev), options);
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
                const classList = ["no-underline"];
                let tagName = "t";
                if (diff[0] === DIFF_INSERT) {
                    classList.push("text-pass", "bg-pass-900");
                    tagName = "ins";
                } else if (diff[0] === DIFF_DELETE) {
                    classList.push("text-fail", "bg-fail-900");
                    tagName = "del";
                }
                return new this({
                    className: classList.join(" "),
                    content: toExplicitString(diff[1]),
                    tagName,
                });
            }),
        });
    }

    /** @param {string} content */
    static green(content) {
        return new this({ className: "text-pass", content });
    }

    /** @param {string} content */
    static red(content) {
        return new this({ className: "text-fail", content });
    }

    /**
     * @param {string} content
     * @param {{ technical?: boolean }} [options]
     */
    static text(content, options) {
        return new this({ ...options, content });
    }
}
