// @ts-check

/** @module @web/core/utils/dnd/draggable_hook_builder_utils - Stateless helpers, constants, and DOM utilities for the draggable hook builder */

/**
 * Pure utilities, constants, and factories for the draggable hook builder.
 *
 * CSS name conversion, event helpers, parameter schema, element attribute
 * save/restore, cleanup lifecycle, and DOM manipulation helpers — all
 * stateless (or self-contained) and independently testable.
 */

import { closestScrollableX, closestScrollableY } from "@web/core/utils/dom/scrolling";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

export const DRAGGABLE_CLASS = "o_draggable";
export const DRAGGED_CLASS = "o_dragged";

export const DEFAULT_ACCEPTED_PARAMS = {
    allowDisconnected: [Boolean], // do not use, introduced for stable versions, to challenge in master
    enable: [Boolean, Function],
    preventDrag: [Function],
    ref: [Object],
    elements: [String],
    handle: [String, Function],
    ignore: [String, Function],
    cursor: [String],
    edgeScrolling: [Object, Function],
    delay: [Number],
    tolerance: [Number],
    touchDelay: [Number],
    iframeWindow: [Object, Function],
};
export const DEFAULT_DEFAULT_PARAMS = {
    allowDisconnected: false,
    elements: `.${DRAGGABLE_CLASS}`,
    enable: true,
    preventDrag: () => false,
    edgeScrolling: {
        speed: 10,
        threshold: 30,
    },
    delay: 0,
    tolerance: 10,
    touchDelay: 300,
};
export const LEFT_CLICK = 0;
export const MANDATORY_PARAMS = ["ref"];
export const WHITE_LISTED_KEYS = ["Alt", "Control", "Meta", "Shift"];

// ---------------------------------------------------------------------------
// Pure functions
// ---------------------------------------------------------------------------

/**
 * Transforms a camelCased string to return its kebab-cased version.
 * Typically used to generate CSS properties from JS objects.
 *
 * @param {string} str
 * @returns {string}
 */
function camelToKebab(str) {
    return str.replace(/([a-z])([A-Z])/g, "$1-$2").toLowerCase();
}

/**
 * @template T
 * @param {T | (() => T)} valueOrFn
 * @returns {T}
 */
export function getReturnValue(valueOrFn) {
    if (typeof valueOrFn === "function") {
        return /** @type {() => T} */ (valueOrFn)();
    }
    return valueOrFn;
}

/**
 * Returns the first scrollable parent of the given element (recursively), or null
 * if none is found. A 'scrollable' element is defined by 2 things:
 *
 * - for either in width or in height: the 'scroll' value is larger than the 'client'
 * value;
 *
 * - its computed 'overflow' property is set to either "auto" or "scroll"
 *
 * If both of these assertions are true, it means that the element can effectively
 * be scrolled on at least one axis.
 * @param {HTMLElement} el
 * @returns {(HTMLElement | null)[]}
 */
export function getScrollParents(el) {
    return [closestScrollableX(el), closestScrollableY(el)];
}

/**
 * Converts a CSS pixel value to a number, removing the 'px' part.
 * @param {string} val
 * @returns {number}
 */
export function pixelValueToNumber(val) {
    return Number(val.endsWith("px") ? val.slice(0, -2) : val);
}

/**
 * @param {Event} ev
 * @param {{ stop?: boolean }} params
 */
export function safePrevent(ev, { stop } = {}) {
    if (ev.cancelable) {
        ev.preventDefault();
        if (stop) {
            ev.stopPropagation();
        }
    }
}

/**
 * @template T
 * @param {T | (() => T)} value
 * @returns {() => T}
 */
export function toFunction(value) {
    return typeof value === "function" ? /** @type {() => T} */ (value) : () => value;
}

// ---------------------------------------------------------------------------
// Element attribute cache & save/restore
// ---------------------------------------------------------------------------

/**
 * Cache containing the elements in which an attribute has been modified by a hook.
 * It is global since multiple draggable hooks can interact with the same elements.
 * @type {Record<string, Set<HTMLElement>>}
 */
const elCache = {};

/**
 * Save the current value of an element's attribute and return a restore function.
 * Uses the global `elCache` to avoid double-saving the same attribute.
 *
 * @param {HTMLElement} el
 * @param {string} attribute
 * @returns {(() => void) | undefined}
 */
export function saveAttribute(el, attribute) {
    const restoreAttribute = () => {
        cache.delete(el);
        if (hasAttribute) {
            el.setAttribute(attribute, originalValue);
        } else {
            el.removeAttribute(attribute);
        }
    };

    if (!(attribute in elCache)) {
        elCache[attribute] = new Set();
    }
    const cache = elCache[attribute];

    if (cache.has(el)) {
        return;
    }

    cache.add(el);
    const hasAttribute = el.hasAttribute(attribute);
    const originalValue = el.getAttribute(attribute);

    return restoreAttribute;
}

// ---------------------------------------------------------------------------
// Factory functions
// ---------------------------------------------------------------------------

/**
 * Create a cleanup lifecycle manager.
 *
 * Registers cleanup functions that are all executed (in LIFO order) when
 * `cleanup()` is called. After cleanup, the optional default cleanup function
 * is re-registered for the next cycle.
 *
 * @param {() => any} [defaultCleanupFn]
 * @returns {{ add: (fn: () => any) => void, cleanup: () => void }}
 */
export function makeCleanupManager(defaultCleanupFn) {
    /**
     * Registers the given cleanup function to be called when cleaning up hooks.
     * @param {() => any} [cleanupFn]
     */
    const add = (cleanupFn) =>
        typeof cleanupFn === "function" && cleanups.push(cleanupFn);

    /**
     * Runs all cleanup functions while clearing the cleanups list.
     */
    const cleanup = () => {
        while (cleanups.length) {
            cleanups.pop()();
        }
        add(defaultCleanupFn);
    };

    const cleanups = [];

    add(defaultCleanupFn);

    return { add, cleanup };
}

/**
 * Create DOM manipulation helpers bound to a cleanup manager.
 *
 * Each DOM operation (addClass, addStyle, setAttribute, etc.) automatically
 * registers an undo function with the cleanup manager so that all changes
 * can be reverted in one call.
 *
 * @param {ReturnType<typeof makeCleanupManager>} cleanup
 */
export function makeDOMHelpers(cleanup) {
    /**
     * @param {HTMLElement} el
     * @param  {...string} classNames
     */
    const addClass = (el, ...classNames) => {
        if (!el || !classNames.length) {
            return;
        }
        cleanup.add(() => el.classList.remove(...classNames));
        el.classList.add(...classNames);
    };

    /**
     * Adds an event listener to be cleaned up after the next drag sequence
     * has stopped.
     * @param {EventTarget} el
     * @param {string} event
     * @param {(...args: any[]) => any} callback
     * @param {AddEventListenerOptions & { noAddedStyle?: boolean }} [options]
     */
    const addListener = (el, event, callback, options = {}) => {
        if (!el || !event || !callback) {
            return;
        }
        const { noAddedStyle } = options;
        delete options.noAddedStyle;
        el.addEventListener(event, callback, options);
        if (!noAddedStyle && /mouse|pointer|touch/.test(event)) {
            // Restore pointer events on elements listening on mouse/pointer/touch events.
            addStyle(/** @type {HTMLElement} */ (el), {
                pointerEvents: "auto",
            });
        }
        cleanup.add(() => el.removeEventListener(event, callback, options));
    };

    /**
     * Adds style to an element to be cleaned up after the next drag sequence has
     * stopped.
     * @param {HTMLElement} el
     * @param {Record<string, string | number>} style
     */
    const addStyle = (el, style) => {
        if (!el || !style || !Object.keys(style).length) {
            return;
        }
        cleanup.add(saveAttribute(el, "style"));
        for (const key in style) {
            const [value, priority] = String(style[key]).split(/\s*!\s*/);
            el.style.setProperty(camelToKebab(key), value, priority);
        }
    };

    /**
     * Returns the bounding rect of the given element. If the `adjust` option is set
     * to true, the rect will be reduced by the padding of the element.
     * @param {HTMLElement} el
     * @param {Object} [options={}]
     * @param {boolean} [options.adjust=false]
     * @returns {DOMRect}
     */
    const getRect = (el, options = {}) => {
        if (!el) {
            return /** @type {DOMRect} */ ({});
        }
        const rect = el.getBoundingClientRect();

        rect.height = el.offsetHeight;

        if (options.adjust) {
            const style = getComputedStyle(el);
            const [pl, pr, pt, pb] = [
                "padding-left",
                "padding-right",
                "padding-top",
                "padding-bottom",
            ].map((prop) => pixelValueToNumber(style.getPropertyValue(prop)));

            rect.x += pl;
            rect.y += pt;
            rect.width -= pl + pr;
            rect.height -= pt + pb;
        }
        return rect;
    };

    /**
     * @param {HTMLElement} el
     * @param {string} attribute
     */
    const removeAttribute = (el, attribute) => {
        if (!el || !attribute) {
            return;
        }
        cleanup.add(saveAttribute(el, attribute));
        el.removeAttribute(attribute);
    };

    /**
     * @param {HTMLElement} el
     * @param {...string} classNames
     */
    const removeClass = (el, ...classNames) => {
        if (!el || !classNames.length) {
            return;
        }
        cleanup.add(saveAttribute(el, "class"));
        el.classList.remove(...classNames);
    };

    /**
     * Adds style to an element to be cleaned up after the next drag sequence has
     * stopped.
     * @param {HTMLElement} el
     * @param {...string} properties
     */
    const removeStyle = (el, ...properties) => {
        if (!el || !properties.length) {
            return;
        }
        cleanup.add(saveAttribute(el, "style"));
        for (const key of properties) {
            el.style.removeProperty(camelToKebab(key));
        }
    };

    /**
     * @param {HTMLElement} el
     * @param {string} attribute
     * @param {any} value
     */
    const setAttribute = (el, attribute, value) => {
        if (!el || !attribute) {
            return;
        }
        cleanup.add(saveAttribute(el, attribute));
        el.setAttribute(attribute, String(value));
    };

    return {
        addClass,
        addListener,
        addStyle,
        getRect,
        removeAttribute,
        removeClass,
        removeStyle,
        setAttribute,
    };
}
