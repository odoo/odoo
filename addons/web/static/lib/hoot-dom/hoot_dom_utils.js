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
 * @typedef {"interaction" | "query" | "server" | "time"} InteractionType
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
    Array: { isArray: $isArray },
    matchMedia,
    navigator: { userAgent: $userAgent },
    Object: { assign: $assign, getPrototypeOf: $getPrototypeOf },
    RegExp,
    SyntaxError,
} = globalThis;
const $toString = Object.prototype.toString;

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
function makeInteractorFn(type, fn, name) {
    return {
        [name](...args) {
            const result = fn(...args);
            if (isInstanceOf(result, Promise)) {
                for (let i = 0; i < args.length; i++) {
                    if (isInstanceOf(args[i], Promise)) {
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
    }[name];
}

function polyfillIsError(value) {
    return $toString.call(value) === "[object Error]";
}

const GRAYS = {
    100: "#f1f5f9",
    200: "#e2e8f0",
    300: "#cbd5e1",
    400: "#94a3b8",
    500: "#64748b",
    600: "#475569",
    700: "#334155",
    800: "#1e293b",
    900: "#0f172a",
};

const COLORS = {
    default: {
        // Generic colors
        black: "#000000",
        white: "#ffffff",

        // Grays
        "gray-100": GRAYS[100],
        "gray-200": GRAYS[200],
        "gray-300": GRAYS[300],
        "gray-400": GRAYS[400],
        "gray-500": GRAYS[500],
        "gray-600": GRAYS[600],
        "gray-700": GRAYS[700],
        "gray-800": GRAYS[800],
        "gray-900": GRAYS[900],
    },
    light: {
        // Generic colors
        primary: "#714b67",
        secondary: "#74b4b9",
        amber: "#f59e0b",
        "amber-900": "#fef3c7",
        blue: "#3b82f6",
        "blue-900": "#dbeafe",
        cyan: "#0891b2",
        "cyan-900": "#e0f2fe",
        emerald: "#047857",
        "emerald-900": "#ecfdf5",
        gray: GRAYS[400],
        lime: "#84cc16",
        "lime-900": "#f7fee7",
        orange: "#ea580c",
        "orange-900": "#ffedd5",
        purple: "#581c87",
        "purple-900": "#f3e8ff",
        rose: "#9f1239",
        "rose-900": "#fecdd3",

        // App colors
        bg: GRAYS[100],
        text: GRAYS[900],
        "status-bg": GRAYS[300],
        "link-text-hover": "var(--primary)",
        "btn-bg": "#714b67",
        "btn-bg-hover": "#624159",
        "btn-text": "#ffffff",
        "bg-result": "rgba(255, 255, 255, 0.6)",
        "border-result": GRAYS[300],
        "border-search": "#d8dadd",
        "shadow-opacity": 0.1,

        // HootReporting colors
        "bg-report": "#ffffff",
        "text-report": "#202124",
        "border-report": "#f0f0f0",
        "bg-report-error": "#fff0f0",
        "text-report-error": "#ff0000",
        "border-report-error": "#ffd6d6",
        "text-report-number": "#1a1aa6",
        "text-report-string": "#c80000",
        "text-report-key": "#881280",
        "text-report-html-tag": "#881280",
        "text-report-html-id": "#1a1aa8",
        "text-report-html-class": "#994500",
    },
    dark: {
        // Generic colors
        primary: "#14b8a6",
        amber: "#fbbf24",
        "amber-900": "#422006",
        blue: "#60a5fa",
        "blue-900": "#172554",
        cyan: "#22d3ee",
        "cyan-900": "#083344",
        emerald: "#34d399",
        "emerald-900": "#064e3b",
        gray: GRAYS[500],
        lime: "#bef264",
        "lime-900": "#365314",
        orange: "#fb923c",
        "orange-900": "#431407",
        purple: "#a855f7",
        "purple-900": "#3b0764",
        rose: "#fb7185",
        "rose-900": "#4c0519",

        // App colors
        bg: GRAYS[900],
        text: GRAYS[100],
        "status-bg": GRAYS[700],
        "btn-bg": "#00dac5",
        "btn-bg-hover": "#00c1ae",
        "btn-text": "#000000",
        "bg-result": "rgba(0, 0, 0, 0.5)",
        "border-result": GRAYS[600],
        "border-search": "#3c3f4c",
        "shadow-opacity": 0.4,

        // HootReporting colors
        "bg-report": "#202124",
        "text-report": "#e8eaed",
        "border-report": "#3a3a3a",
        "bg-report-error": "#290000",
        "text-report-error": "#ff8080",
        "border-report-error": "#5c0000",
        "text-report-number": "#9980ff",
        "text-report-string": "#f28b54",
        "text-report-key": "#5db0d7",
        "text-report-html-tag": "#5db0d7",
        "text-report-html-id": "#f29364",
        "text-report-html-class": "#9bbbdc",
    },
};
const DEBUG_NAMESPACE = "hoot";

const isError = typeof Error.isError === "function" ? Error.isError : polyfillIsError;
const interactionBus = new EventTarget();
const preferredColorScheme = matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";

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
 * @param {keyof typeof COLORS} [scheme]
 */
export function getAllColors(scheme) {
    return scheme ? COLORS[scheme] : COLORS;
}

/**
 * @param {keyof typeof COLORS["light"]} varName
 */
export function getColorHex(varName) {
    return COLORS[preferredColorScheme][varName];
}

export function getPreferredColorScheme() {
    return preferredColorScheme;
}

/**
 * @param {Node} node
 */
export function getTag(node) {
    return node?.nodeName?.toLowerCase() || "";
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
 * @returns {boolean}
 */
export function isFirefox() {
    return /firefox/i.test($userAgent);
}

/**
 * Cross-realm equivalent to 'instanceof'.
 * Can be called with multiple constructors, and will return true if the given object
 * is an instance of any of them.
 *
 * @param {unknown} instance
 * @param {...{ name: string }} classes
 */
export function isInstanceOf(instance, ...classes) {
    if (!classes.length) {
        return instance instanceof classes[0];
    }
    if (!instance || Object(instance) !== instance) {
        // Object is falsy or a primitive (null, undefined and primitives cannot be the instance of anything)
        return false;
    }
    for (const cls of classes) {
        if (instance instanceof cls) {
            return true;
        }
        const targetName = cls.name;
        if (!targetName) {
            return false;
        }
        if (targetName === "Array") {
            return $isArray(instance);
        }
        if (targetName === "Error") {
            return isError(instance);
        }
        if ($toString.call(instance) === `[object ${targetName}]`) {
            return true;
        }
        let { constructor } = instance;
        while (constructor) {
            if (constructor.name === targetName) {
                return true;
            }
            constructor = $getPrototypeOf(constructor);
        }
    }
    return false;
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
    return !!(object && typeof object === "object" && object[Symbol.iterator]);
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
            if (isInstanceOf(error, SyntaxError) && options?.safe) {
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
    /**
     * @param  {...any} helpers
     */
    constructor(...helpers) {
        $assign(this, ...helpers);
    }
}

export const REGEX_MARKER = "/";

// Common regular expressions
export const R_REGEX = new RegExp(`^${REGEX_MARKER}(.*)${REGEX_MARKER}([dgimsuvy]+)?$`);
export const R_WHITE_SPACE = /\s+/g;
