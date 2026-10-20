export class PairSet {
    constructor() {
        this.map = new Map(); // map of [1] => Set<[2]>
    }
    add(elem1, elem2) {
        if (!this.map.has(elem1)) {
            this.map.set(elem1, new Set());
        }
        this.map.get(elem1).add(elem2);
    }
    has(elem1, elem2) {
        if (!this.map.has(elem1)) {
            return false;
        }
        return this.map.get(elem1).has(elem2);
    }
    delete(elem1, elem2) {
        if (!this.map.has(elem1)) {
            return;
        }
        const s = this.map.get(elem1);
        s.delete(elem2);
        if (!s.size) {
            this.map.delete(elem1);
        }
    }
}

export {
    BUTTON_HANDLER_SELECTOR,
    DEBOUNCE,
    makeAsyncHandler,
    makeButtonHandler,
} from "@web/public/button_handler";

/**
 * Patches a "t-" entry of a dynamic content.
 *
 * @param {Object} dynamicContent
 * @param {string} selector
 * @param {string} t
 * @param {any|function} replacement, if a function, takes the element and the
 *     replaced's function output as parameters
 */
export function patchDynamicContentEntry(dynamicContent, selector, t, replacement) {
    dynamicContent[selector] = dynamicContent[selector] || {};
    const forSelector = dynamicContent[selector];
    if (replacement === undefined) {
        delete forSelector[t];
    } else if (typeof replacement === "function" && t !== "t-component") {
        if (!forSelector[t]) {
            forSelector[t] = () => {};
        }
        const oldFn = forSelector[t];
        if (["t-att-class", "t-att-style"].includes(t)) {
            forSelector[t] = (el, oldResult) => {
                const result = oldResult || {};
                Object.assign(result, oldFn(el, result));
                Object.assign(result, replacement(el, result));
                return result;
            };
        } else if (t.startsWith("t-on-")) {
            forSelector[t] = (el, ...args) => replacement(el, oldFn, ...args);
        } else {
            forSelector[t] = (el, oldResult) => {
                let result = oldResult;
                result = oldFn(el, result);
                result = replacement(el, result);
                return result;
            };
        }
    } else {
        forSelector[t] = replacement;
    }
}

/**
 * Patches several entries in a dynamicContent.
 * Example usage:
 * patchDynamicContent(this.dynamicContent, {
 *     _root: {
 *         "t-att-class": (el, old) => ({
 *             "test": this.condition && old.test,
 *         }),
 *         "t-on-click": (el, oldFn) => {
 *             oldFn(el);
 *             this.doMoreStuff();
 *         },
 *     },
 * })
 *
 * @param {Object} dynamicContent
 * @param {Object} replacement
 */
export function patchDynamicContent(dynamicContent, replacement) {
    for (const [selector, forSelector] of Object.entries(replacement)) {
        for (const [t, forT] of Object.entries(forSelector)) {
            patchDynamicContentEntry(dynamicContent, selector, t, forT);
        }
    }
}
