/** @odoo-module */

import { queryAll } from "@odoo/hoot-dom";
import { reactive, useEffect, useExternalListener } from "@odoo/owl";
import { isNode } from "@web/../lib/hoot-dom/helpers/dom";
import { isIterable, toSelector } from "@web/../lib/hoot-dom/hoot_dom_utils";
import { DiffMatchPatch } from "./lib/diff_match_patch";
import { getRunner } from "./main_runner";

/**
 * @typedef {ArgumentPrimitive | `${ArgumentPrimitive}[]` | null} ArgumentType
 *
 * @typedef {"any"
 *  | "bigint"
 *  | "boolean"
 *  | "date"
 *  | "error"
 *  | "function"
 *  | "integer"
 *  | "node"
 *  | "null"
 *  | "number"
 *  | "object"
 *  | "regex"
 *  | "string"
 *  | "symbol"
 *  | "url"
 *  | "undefined"} ArgumentPrimitive
 *
 * @typedef {[string, ArgumentType]} Label
 *
 * @typedef {"expected" | "group" | "received" | "technical"} MarkupType
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
 *
 * @typedef {import("./core/runner").Runner} Runner
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
    Array: { from: $from, isArray: $isArray },
    Boolean,
    clearTimeout,
    console: { debug: $debug },
    Date,
    Error,
    ErrorEvent,
    JSON: { parse: $parse, stringify: $stringify },
    localStorage,
    Map,
    Math: { floor: $floor, max: $max, min: $min },
    Number: { isInteger: $isInteger, isNaN: $isNaN, parseFloat: $parseFloat },
    navigator: { clipboard: $clipboard },
    Object: {
        assign: $assign,
        create: $create,
        defineProperty: $defineProperty,
        entries: $entries,
        fromEntries: $fromEntries,
        getOwnPropertyDescriptors: $getOwnPropertyDescriptors,
        getPrototypeOf: $getPrototypeOf,
        keys: $keys,
    },
    Promise,
    PromiseRejectionEvent,
    Reflect: { ownKeys: $ownKeys },
    RegExp,
    Set,
    setTimeout,
    String,
    Symbol,
    TypeError,
    WeakSet,
    window,
} = globalThis;
/** @type {Storage["getItem"]} */
const $getItem = localStorage.getItem.bind(localStorage);
/** @type {Clipboard["readText"]} */
const $readText = $clipboard?.readText.bind($clipboard);
/** @type {Storage["setItem"]} */
const $setItem = localStorage.setItem.bind(localStorage);
/** @type {Storage["removeItem"]} */
const $removeItem = localStorage.removeItem.bind(localStorage);
/** @type {Clipboard["writeText"]} */
const $writeText = $clipboard?.writeText.bind($clipboard);

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * Returns the constructor of the given value, and if it is "Object": tries to
 * infer the actual constructor name from the string representation of the object.
 *
 * This is needed for cursed JavaScript objects such as "Arguments", which is an
 * array-like object without a proper constructor.
 *
 * @param {any} value
 */
const getConstructor = (value) => {
    const { constructor } = value;
    if (constructor !== Object) {
        return constructor || { name: null };
    }
    const str = value.toString();
    const match = str.match(R_OBJECT);
    if (!match || match[1] === "Object") {
        return constructor;
    }

    // Custom constructor
    const className = match[1];
    if (!objectConstructors.has(className)) {
        objectConstructors.set(
            className,
            class {
                static name = className;
                constructor(...values) {
                    $assign(this, ...values);
                }
            }
        );
    }
    return objectConstructors.get(className);
};

/**
 * @param {(...args: any[]) => any} fn
 */
const getFunctionString = (fn) => {
    if (R_CLASS.test(fn.name)) {
        return `${fn.name ? `class ${fn.name}` : "anonymous class"} { ${ELLIPSIS} }`;
    }
    const strFn = fn.toString();
    const prefix = R_ASYNC_FUNCTION.test(strFn) ? "async " : "";

    if (R_NAMED_FUNCTION.test(strFn)) {
        return `${
            fn.name ? `${prefix}function ${fn.name}` : `anonymous ${prefix}function`
        }() { ${ELLIPSIS} }`;
    }

    const args = fn.length ? "...args" : "";
    return `${prefix}(${args}) => { ${ELLIPSIS} }`;
};

/**
 * @template {(...args: any[]) => T} T
 * @param {T} instanceGetter
 * @returns {T}
 */
const memoize = (instanceGetter) => {
    let called = false;
    let value;
    return function memoized(...args) {
        if (!called) {
            called = true;
            value = instanceGetter(...args);
        }
        return value;
    };
};

/**
 * @param {string} value
 * @param {number} [length=MAX_HUMAN_READABLE_SIZE]
 */
const truncate = (value, length = MAX_HUMAN_READABLE_SIZE) => {
    const strValue = String(value);
    return strValue.length <= length ? strValue : strValue.slice(0, length) + ELLIPSIS;
};

/**
 * @param {unknown} value
 * @param {number} length
 * @returns {[string, number]}
 */
const _formatHumanReadable = (value, length) => {
    let humanReadableValue = "";
    if (typeof value === "string") {
        humanReadableValue = stringify(truncate(value));
    } else if (typeof value === "number") {
        if (value << 0 === value) {
            humanReadableValue = truncate(value);
        } else {
            let fixed = value.toFixed(3);
            while (fixed.endsWith("0")) {
                fixed = fixed.slice(0, -1);
            }
            humanReadableValue = truncate(fixed);
        }
    } else if (typeof value === "function") {
        humanReadableValue = getFunctionString(value);
    } else if (value && typeof value === "object") {
        if (value instanceof RegExp || value instanceof URL) {
            humanReadableValue = truncate(value);
        } else if (value instanceof Date) {
            humanReadableValue = value.toISOString();
        } else if (isNode(value)) {
            const name = value.nodeName.toLowerCase();
            humanReadableValue = value.nodeType === Node.ELEMENT_NODE ? `<${name}>` : name;
        } else if (isIterable(value)) {
            const values = [...value];
            if (values.length === 1 && isNode(values[0])) {
                // Special case for single-element nodes arrays
                const hValue = _formatHumanReadable(values[0], length);
                humanReadableValue = hValue;
                length += hValue.length;
            } else {
                const constructor = getConstructor(value);
                const constructorPrefix =
                    constructor.name === "Array" ? "" : `${constructor.name} `;
                const content = [];
                if (values.length) {
                    const bitSize = $max(
                        MIN_HUMAN_READABLE_SIZE,
                        $floor(MAX_HUMAN_READABLE_SIZE / values.length)
                    );
                    for (const val of values) {
                        const hVal = truncate(_formatHumanReadable(val, length), bitSize);
                        content.push(hVal);
                        length += hVal.length;
                        if (length > MAX_HUMAN_READABLE_SIZE) {
                            content.push(ELLIPSIS);
                            break;
                        }
                    }
                }
                humanReadableValue = `${constructorPrefix}[${truncate(content.join(", "))}]`;
            }
        } else {
            const keys = $keys(value);
            const constructor = getConstructor(value);
            const constructorPrefix = constructor.name === "Object" ? "" : `${constructor.name} `;
            const content = [];
            if (constructor.name !== "Window" && keys.length) {
                const bitSize = $max(
                    MIN_HUMAN_READABLE_SIZE,
                    $floor(MAX_HUMAN_READABLE_SIZE / keys.length)
                );
                const descriptors = $getOwnPropertyDescriptors(value);
                for (const key of keys) {
                    if (!("value" in descriptors[key])) {
                        continue;
                    }
                    const hVal = truncate(
                        _formatHumanReadable(descriptors[key].value, length),
                        bitSize
                    );
                    content.push(`${key}: ${hVal}`);
                    length += hVal.length;
                    if (length > MAX_HUMAN_READABLE_SIZE) {
                        content.push(ELLIPSIS);
                        break;
                    }
                }
            }
            humanReadableValue = `${constructorPrefix}{ ${truncate(content.join(", "))} }`;
        }
    } else {
        humanReadableValue = String(value);
    }

    return humanReadableValue;
};

const BACK_TICK = "`";
const DOUBLE_QUOTES = '"';
const SINGLE_QUOTE = "'";

const ELLIPSIS = "…";
const MAX_HUMAN_READABLE_SIZE = 80;
const MIN_HUMAN_READABLE_SIZE = 8;

const R_ASYNC_FUNCTION = /^\s*async/;
const R_CLASS = /^[A-Z][a-z]/;
const R_NAMED_FUNCTION = /^\s*(async\s+)?function/;
const R_INVISIBLE_CHARACTERS = /[\u00a0\u200b-\u200d\ufeff]/g;
const R_OBJECT = /^\[object ([\w-]+)\]$/;

const dmp = new DiffMatchPatch();
const { DIFF_INSERT, DIFF_DELETE } = DiffMatchPatch;

const labelObjects = new WeakSet();
const objectConstructors = new Map();
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
        $debug(`Copied to clipboard: ${stringify(text)}`);
    } catch (error) {
        console.warn("Could not copy to clipboard:", error);
    }
}

/**
 * @template T
 * @template {(previous: T | null) => T} F
 * @param {F} instanceGetter
 * @param {() => any} [afterCallback]
 * @returns {F}
 */
export function createJobScopedGetter(instanceGetter, afterCallback) {
    /** @type {F} */
    const getInstance = () => {
        if (runner.dry) {
            return memoized();
        }

        const currentJob = runner.state.currentTest || runner.suiteStack.at(-1) || runner;
        if (!instances.has(currentJob)) {
            const parentInstance = [...instances.values()].at(-1);
            instances.set(currentJob, instanceGetter(parentInstance));

            if (canCallAfter) {
                runner.after(() => {
                    instances.delete(currentJob);

                    canCallAfter = false;
                    afterCallback?.();
                    canCallAfter = true;
                });
            }
        }

        return instances.get(currentJob);
    };

    const memoized = memoize(instanceGetter);

    /** @type {Map<Job, T>} */
    const instances = new Map();
    const runner = getRunner();
    let canCallAfter = true;

    runner.after(() => instances.clear());

    return getInstance;
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
 * @param {Record<keyof T, PropertyDescriptor>} descriptors
 * @returns {T}
 */
export function createMock(target, descriptors) {
    let owner = target;
    let keys = $ownKeys(owner);
    while (!keys.length) {
        owner = $getPrototypeOf(owner);
        keys = $ownKeys(owner);
    }

    // Copy original descriptors
    const mock = $assign($create(owner), target);
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
 * @template T
 * @param {T} value
 * @returns {T}
 */
export function deepCopy(value) {
    if (!value) {
        return value;
    }
    if (typeof value === "function") {
        if (value.name) {
            return `<function ${value.name}>`;
        } else {
            return "<anonymous function>";
        }
    }

    if (typeof value === "object" && !Markup.isMarkup(value)) {
        if (value instanceof String || value instanceof Number || value instanceof Boolean) {
            return value;
        }
        if (isNode(value)) {
            // Nodes
            return value.cloneNode(true);
        } else if (value instanceof Date || value instanceof RegExp) {
            // Dates & regular expressions
            return new (getConstructor(value))(value);
        } else if (isIterable(value)) {
            // Iterables
            const values = [...value].map(deepCopy);
            return $isArray(value) ? values : new (getConstructor(value))(values);
        } else {
            // Other objects
            return $fromEntries($ownKeys(value).map((key) => [key, deepCopy(value[key])]));
        }
    }
    return value;
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
    if (aType !== typeof b || !a || !b || aType !== "object") {
        return false;
    }

    cache.add(a);
    if (isNode(a)) {
        return isNode(b) && a.isEqualNode(b);
    }
    if (a instanceof File) {
        // Files
        return a.name === b.name && a.size === b.size && a.type === b.type;
    }
    if (a instanceof Date || a instanceof RegExp) {
        // Dates & regular expressions
        return strictEqual(String(a), String(b));
    }

    const aIsIterable = isIterable(a);
    if (aIsIterable !== isIterable(b)) {
        return false;
    }
    if (!aIsIterable) {
        // All non-iterable objects
        const aKeys = $ownKeys(a);
        return (
            aKeys.length === $ownKeys(b).length &&
            aKeys.every((key) => deepEqual(a[key], b[key], cache))
        );
    }

    // Iterables
    const aIsArray = $isArray(a);
    if (aIsArray !== $isArray(b)) {
        return false;
    }
    if (!aIsArray) {
        a = [...a];
        b = [...b];
    }
    return a.length === b.length && a.every((v, i) => deepEqual(v, b[i], cache));
}

/**
 * @param {any[]} args
 * @param {...(ArgumentType | ArgumentType[])} argumentsDefs
 */
export function ensureArguments(args, ...argumentsDefs) {
    if (args.length > argumentsDefs.length) {
        throw new HootError(
            `expected a maximum of ${argumentsDefs.length} arguments and got ${args.length}`
        );
    }
    for (let i = 0; i < argumentsDefs.length; i++) {
        const value = args[i];
        const acceptedType = argumentsDefs[i];
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
        return ensureError(value.error || value.message);
    }
    if (value instanceof PromiseRejectionEvent) {
        return ensureError(value.reason || value.message);
    }
    return new Error(String(value || "unknown error"));
}

/**
 * @param {unknown} value
 * @returns {string}
 */
export function formatHumanReadable(value) {
    return _formatHumanReadable(value, 0);
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
    if (value === S_ANY || value === S_NONE) {
        return "";
    } else if (typeof value === "string") {
        return `${baseIndent}${stringify(value)}`;
    } else if (typeof value === "number") {
        return `${baseIndent}${value << 0 === value ? String(value) : value.toFixed(3)}`;
    } else if (typeof value === "function") {
        return `${baseIndent}${getFunctionString(value)}`;
    } else if (value && typeof value === "object") {
        if (cache.has(value)) {
            return `${baseIndent}${$isArray(value) ? `[${ELLIPSIS}]` : `{ ${ELLIPSIS} }`}`;
        } else {
            cache.add(value);
            const startIndent = " ".repeat((depth + 1) * 2);
            const endIndent = " ".repeat(depth * 2);
            const constructor = getConstructor(value);
            if (value instanceof RegExp || value instanceof Error) {
                return `${baseIndent}${value.toString()}`;
            } else if (value instanceof Date) {
                return `${baseIndent}${value.toISOString()}`;
            } else if (isNode(value)) {
                return `<${toSelector(value)} />`;
            } else if (isIterable(value)) {
                const proto = constructor.name === "Array" ? "" : `${constructor.name} `;
                const content = [...value].map(
                    (val) =>
                        `${startIndent}${formatTechnical(val, {
                            cache,
                            depth: depth + 1,
                            isObjectValue: true,
                        })},\n`
                );
                return `${baseIndent}${proto}[${
                    content.length ? `\n${content.join("")}${endIndent}` : ""
                }]`;
            } else {
                const proto =
                    !constructor.name || constructor.name === "Object"
                        ? ""
                        : `${constructor.name} `;
                const content = $ownKeys(value)
                    .sort()
                    .map(
                        (key) =>
                            `${startIndent}${key}: ${formatTechnical(value[key], {
                                cache,
                                depth: depth + 1,
                                isObjectValue: true,
                            })},\n`
                    );
                return `${baseIndent}${proto}{${
                    content.length ? `\n${content.join("")}${endIndent}` : ""
                }}`;
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
            const str = String($floor(value));
            return `${str.slice(0, -3) + "," + str.slice(-3)}${unit}`;
        }
        return value + unit;
    }

    value = $floor(value / 1_000);

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
 * @param {unknown} value
 * @returns {ArgumentType}
 */
export function getTypeOf(value) {
    const type = typeof value;
    switch (type) {
        case "number": {
            return $isInteger(value) ? "integer" : "number";
        }
        case "object": {
            if (value === null) {
                return "null";
            }
            if (value instanceof Date) {
                return "date";
            }
            if (value instanceof Error) {
                return "error";
            }
            if (isNode(value)) {
                return "node";
            }
            if (value instanceof RegExp) {
                return "regex";
            }
            if (value instanceof URL) {
                return "url";
            }
            if ($isArray(value)) {
                const types = [...value].map(getTypeOf);
                const arrayType = new Set(types).size === 1 ? types[0] : "any";
                if (arrayType.endsWith("[]")) {
                    return "object[]";
                } else {
                    return `${arrayType}[]`;
                }
            }
            /** fallsthrough */
        }
        default: {
            return type;
        }
    }
}

export function hasClipboard() {
    return Boolean($clipboard);
}

/**
 * @param {[string, ArgumentType]} label
 */
export function isLabel(label) {
    return labelObjects.has(label);
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
        case "null":
        case null:
        case undefined:
            return value === null || value === undefined;
        case "any":
            return true;
        case "date":
            return value instanceof Date;
        case "error":
            return value instanceof Error;
        case "integer":
            return $isInteger(value);
        case "node":
            return isNode(value);
        case "regex":
            return value instanceof RegExp;
        case "url":
            return value instanceof URL;
        default:
            return typeof value === type;
    }
}

/**
 * Returns the edit distance between 2 strings
 *
 * @param {string} a
 * @param {string} b
 * @returns {number}
 * @example
 *  levenshtein("abc", "àbc"); // => 0
 * @example
 *  levenshtein("abc", "def"); // => 3
 * @example
 *  levenshtein("abc", "adc"); // => 1
 */
export function levenshtein(a, b) {
    if (!a.length) {
        return b.length;
    }
    if (!b.length) {
        return a.length;
    }
    const dp = $from({ length: b.length + 1 }, (_, i) => i);
    for (let i = 1; i <= a.length; i++) {
        let prev = dp[0];
        dp[0] = i;
        for (let j = 1; j <= b.length; j++) {
            const temp = dp[j];
            dp[j] = a[i - 1] === b[j - 1] ? prev : 1 + $min(dp[j - 1], dp[j], prev);
            prev = temp;
        }
    }
    return dp[b.length];
}

/**
 * Returns a list of items that match the given pattern, ordered by their 'score'
 * (descending). A higher score means that the match is closer (e.g. consecutive
 * letters).
 *
 * @template {{ key: string }} T
 * @param {string | RegExp} pattern normalized string or RegExp
 * @param {Iterable<T>} items
 * @param {keyof T} [property]
 * @returns {T[]}
 */
export function lookup(pattern, items, property = "key") {
    /** @type {T[]} */
    const result = [];
    if (pattern instanceof RegExp) {
        // Regex lookup
        for (const item of items) {
            if (pattern.test(item[property])) {
                result.push(item);
            }
        }
    } else {
        // Fuzzy lookup
        const scores = new Map();
        for (const item of items) {
            if (scores.has(item)) {
                result.push(item);
                continue;
            }
            const score = getFuzzyScore(pattern, item[property]);
            if (score > 0) {
                scores.set(item, score);
                result.push(item);
            }
        }
        result.sort((a, b) => scores.get(b) - scores.get(a));
    }
    return result;
}

/**
 * @template [T=any]
 * @param {T} value
 * @param {ArgumentType} type
 */
export function makeLabel(value, type) {
    if (isLabel(value)) {
        [value, type] = value;
    } else if (type === undefined) {
        type = getTypeOf(value);
    }
    if (type !== null) {
        value = formatHumanReadable(value);
    }
    const label = [value, type];
    labelObjects.add(label);
    return label;
}

/**
 * Special label type used in test results
 * @param {string} className
 */
export function makeLabelIcon(className) {
    const label = [className, "icon"];
    labelObjects.add(label);
    return label;
}

/**
 * @template {keyof Runner} T
 * @param {T} name
 * @returns {Runner[T]}
 */
export function makeRuntimeHook(name) {
    return {
        [name](...callbacks) {
            const runner = getRunner();
            if (runner.dry) {
                return;
            }
            let valid = Boolean(runner.suiteStack.length);
            const last = callbacks.at(-1);
            if (last && typeof last === "object") {
                callbacks.pop();
                valid ||= Boolean(last.global);
            }
            if (!valid) {
                throw new HootError(`cannot call "${name}" callback outside of a suite`);
            }
            return runner[name](...callbacks);
        },
    }[name];
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
            strValue = getConstructor(value).name;
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

/**
 * @param {unknown} number
 */
export function ordinal(number) {
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
}

export async function paste() {
    try {
        await $readText();
    } catch (error) {
        console.warn("Could not paste from clipboard:", error);
    }
}

/**
 * @param {string} key
 */
export function storageGet(key) {
    const value = $getItem(key);
    if (value) {
        try {
            const parsed = $parse(value);
            return parsed;
        } catch (err) {
            console.warn(`Couldn't parse value for storage key "${key}":`, err);
            $removeItem(key);
        }
    }
    return null;
}

/**
 * @param {string} key
 * @param {any} value
 */
export function storageSet(key, value) {
    return $setItem(key, $stringify(value));
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
 * @param {unknown} value
 */
export function stringify(value) {
    const strValue = String(value);
    const quotes = strValue.includes(DOUBLE_QUOTES)
        ? strValue.includes(SINGLE_QUOTE)
            ? BACK_TICK
            : SINGLE_QUOTE
        : DOUBLE_QUOTES;
    return quotes + strValue + quotes;
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

/**
 * Replaces invisible characters in a given value with their unicode value.
 *
 * @param {unknown} value
 */
export function toExplicitString(value) {
    const strValue = String(value);
    switch (strValue) {
        case "\n": {
            return "\\n";
        }
        case "\t": {
            return "\\t";
        }
    }
    return strValue.replace(
        R_INVISIBLE_CHARACTERS,
        (char) => `\\u${char.charCodeAt(0).toString(16).padStart(4, "0")}`
    );
}

/**
 * @param {{ el?: HTMLElement }} ref
 */
export function useAutofocus(ref) {
    let displayed = new Set();
    useEffect(() => {
        if (!ref.el) {
            return;
        }
        const nextDisplayed = new Set();
        for (const element of ref.el.querySelectorAll("[autofocus]")) {
            if (!displayed.has(element)) {
                element.focus();
                if (["INPUT", "TEXTAREA"].includes(element.tagName)) {
                    element.selectionStart = 0;
                    element.selectionEnd = element.value;
                }
            }
            nextDisplayed.add(element);
        }
        displayed = nextDisplayed;
    });
}

/** @type {EventTarget["addEventListener"]} */
export function useWindowListener(type, callback, options) {
    return useExternalListener(windowTarget, type, (ev) => ev.isTrusted && callback(ev), options);
}

export class Callbacks {
    /** @type {Map<string, ((...args: any[]) => MaybePromise<((...args: any[]) => void) | void>)[]>} */
    _callbacks = new Map();

    /**
     * @template P
     * @param {string} type
     * @param {MaybePromise<(...args: P[]) => MaybePromise<((...args: P[]) => void) | void>>} callback
     * @param {boolean} [once]
     */
    add(type, callback, once) {
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
                this._callbacks.set(
                    type,
                    this._callbacks.get(type).filter((fn) => fn !== callback)
                );
                return originalCallback(...args);
            };
            $assign(callback, { original: originalCallback });
        }

        if (!this._callbacks.has(type)) {
            this._callbacks.set(type, []);
        }
        if (type.startsWith("after")) {
            this._callbacks.get(type).unshift(callback);
        } else {
            this._callbacks.get(type).push(callback);
        }
    }

    /**
     * @template T
     * @param {string} type
     * @param {T} detail
     * @param {(error: Error) => any} [onError]
     */
    async call(type, detail, onError) {
        const fns = this._callbacks.get(type);
        if (!fns?.length) {
            return;
        }

        const afterCallback = this._getAfterCallback(type);
        for (const fn of fns) {
            try {
                const result = await fn(detail);
                afterCallback(result);
            } catch (error) {
                if (typeof onError === "function") {
                    onError(error);
                } else {
                    throw error;
                }
            }
        }
    }

    /**
     * @template T
     * @param {string} type
     * @param {T} detail
     * @param {(error: Error) => any} [onError]
     */
    callSync(type, detail, onError) {
        const fns = this._callbacks.get(type);
        if (!fns?.length) {
            return;
        }

        const afterCallback = this._getAfterCallback(type);
        for (const fn of fns) {
            try {
                const result = fn(detail);
                afterCallback(result);
            } catch (error) {
                if (typeof onError === "function") {
                    onError(error);
                } else {
                    throw error;
                }
            }
        }
    }

    clear() {
        this._callbacks.clear();
    }

    /**
     * @param {string} type
     */
    _getAfterCallback(type) {
        if (!type.startsWith("before")) {
            return () => {};
        }
        const relatedType = `after${type.slice(6)}`;
        return (result) => this.add(relatedType, result, true);
    }
}

/**
 * @template T
 * @extends {Map<Element, T>}
 */
export class ElementMap extends Map {
    /** @type {string | null} */
    selector = null;

    /**
     * @param {Target} target
     * @param {(element: Element) => T} [mapFn]
     */
    constructor(target, mapFn) {
        const mapValues = [];
        for (const element of queryAll(target)) {
            mapValues.push([element, mapFn ? mapFn(element) : element]);
        }

        super(mapValues);

        if (typeof target === "string") {
            this.selector = target;
        }
    }

    /**
     * @param {(value: T, element: Element, map: ElementMap) => boolean} predicate
     * @returns {boolean}
     */
    every(predicate) {
        if (!this.size) {
            return false;
        }
        for (const [el, value] of this) {
            const pass = predicate(value, el, this);
            if (!pass) {
                return false;
            }
        }
        return true;
    }

    /**
     * Returns a flat list of values mapped by the given function.
     * Additionnaly, group headers are inserted if the map has more than 1 element.
     *
     * @template [N=T]
     * @param {(value: T, element: Element, map: ElementMap) => N[]} mapFn
     * @param {(value: T, element: Element, map: ElementMap) => boolean} predicate
     * @returns {N[]}
     */
    mapFailedDetails(mapFn, predicate) {
        if (!this.size) {
            return [Markup.received("Elements found:", 0)];
        }
        const result = [];
        let groupIndex = 1;
        for (const [el, value] of this) {
            result.push(
                new Markup({
                    content: el,
                    groupIndex: groupIndex++,
                    type: "group",
                }),
                ...Markup.resolveDetails(mapFn(value, el, this), predicate(value, el, this))
            );
        }
        return result;
    }
}

export class HootError extends Error {
    name = "HootError";
}

/** @template [T=string] */
export class Markup {
    className = "";
    /** @type {T} */
    content = "";
    tagName = "div";
    /** @type {MarkupType} */
    type;
    /** @type {number} */
    groupIndex;

    /**
     * @param {Partial<Markup<T>>} params
     */
    constructor(params) {
        $assign(this, params);

        this.content = deepCopy(this.content);
    }

    /**
     * @param {unknown} expected
     * @param {unknown} actual
     */
    static diff(expected, actual) {
        const eType = typeof expected;
        if (eType !== typeof actual || !(eType === "object" || eType === "string")) {
            // Cannot diff
            return null;
        }
        let hasDiff;
        const diff = dmp
            .diff_main(formatTechnical(expected), formatTechnical(actual))
            .map((diff) => {
                let className = "no-underline";
                let tagName = "t";
                if (diff[0] === DIFF_INSERT) {
                    className += " text-emerald bg-emerald-900";
                    tagName = "ins";
                    hasDiff = true;
                } else if (diff[0] === DIFF_DELETE) {
                    className += " text-rose bg-rose-900";
                    tagName = "del";
                    hasDiff = true;
                }
                return new Markup({
                    className,
                    content: toExplicitString(diff[1]),
                    tagName,
                });
            });
        return hasDiff
            ? [
                  new Markup({ content: "Diff:" }),
                  new Markup({
                      content: diff,
                      type: "technical",
                  }),
              ]
            : null;
    }

    /**
     * @param {string} content
     * @param {unknown} value
     */
    static expected(content, value) {
        return [new Markup({ content, type: "expected" }), deepCopy(value)];
    }

    /**
     * @param {unknown} object
     * @param {MarkupType} [type]
     */
    static isMarkup(object, type) {
        if (!(object instanceof Markup)) {
            return false;
        }
        return !type || object.type === type;
    }

    /**
     * @param {string} content
     * @param {unknown} value
     */
    static received(content, value) {
        return [new Markup({ content, type: "received" }), deepCopy(value)];
    }

    /**
     * @param {Markup[][]} details
     * @param {boolean} [pass=false]
     */
    static resolveDetails(details, pass = false) {
        const result = [];
        for (let detail of details) {
            if (!detail) {
                continue;
            }
            if (isIterable(detail)) {
                for (const detailPart of detail) {
                    if (Markup.isMarkup(detailPart, "expected")) {
                        if (pass) {
                            detail = null;
                            break;
                        }
                        detailPart.className ||= "text-emerald";
                    } else if (Markup.isMarkup(detailPart, "received")) {
                        detailPart.className ||= pass ? "text-emerald" : "text-rose";
                    }
                }
            }
            if (detail) {
                result.push(detail);
            }
        }
        return result;
    }

    /**
     * @param {string} content
     * @param {unknown} value
     */
    static text(content, value) {
        return [new Markup({ content }), deepCopy(value)];
    }
}

/**
 * Centralized version of {@link EventTarget} to make cleanups more streamlined.
 */
export class MockEventTarget extends EventTarget {
    /** @type {string[]} */
    static publicListeners = [];

    constructor() {
        super(...arguments);

        for (const type of this.constructor.publicListeners) {
            let listener = null;
            $defineProperty(this, `on${type}`, {
                get() {
                    return listener;
                },
                set(value) {
                    if (listener) {
                        this.removeEventListener(type, listener);
                    }
                    listener = value;
                    if (listener) {
                        this.addEventListener(type, listener);
                    }
                },
            });
        }
    }
}

export const CASE_EVENT_TYPES = {
    assertion: {
        value: 0b1,
        icon: "fa-check",
        color: "emerald",
    },
    error: {
        value: 0b10,
        icon: "fa-exclamation",
        color: "rose",
    },
    interaction: {
        value: 0b100,
        icon: "fa-bolt",
        color: "purple",
    },
    query: {
        value: 0b1000,
        icon: "fa-search text-sm",
        color: "amber",
    },
    server: {
        value: 0b10000,
        icon: "fa-globe",
        color: "lime",
    },
    step: {
        value: 0b100000,
        icon: "fa-arrow-right text-sm",
        color: "orange",
    },
};
export const DEFAULT_EVENT_TYPES = CASE_EVENT_TYPES.assertion.value | CASE_EVENT_TYPES.error.value;

export const INCLUDE_LEVEL = {
    url: 1,
    tag: 2,
    preset: 3,
};

export const MIME_TYPE = {
    blob: "application/octet-stream",
    json: "application/json",
    text: "text/plain",
};

export const STORAGE = {
    failed: "hoot-failed-tests",
    scheme: "hoot-color-scheme",
    searches: "hoot-latest-searches",
};

export const S_ANY = Symbol("any value");
export const S_NONE = Symbol("no value");
