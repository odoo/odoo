/** @odoo-module **/

import { browser } from "../browser/browser";

/**
 * Returns a function, that, as long as it continues to be invoked, will not
 * be triggered. The function will be called after it stops being called for
 * N milliseconds. If `immediate` is passed, trigger the function on the
 * leading edge, instead of the trailing.
 *
 * Inspired by https://davidwalsh.name/javascript-debounce-function
 * @param {Function} func
 * @param {number} wait
 * @param {boolean} [immediate=false]
 * @returns {Function}
 */
export function debounce(func, wait, immediate = false) {
    let timeout;
    const funcName = func.name ? func.name + " (debounce)" : "debounce";
    return {
        [funcName](...args) {
            const context = this;
            function later() {
                if (!immediate) {
                    func.apply(context, args);
                }
            }
            const callNow = immediate && !timeout;
            browser.clearTimeout(timeout);
            timeout = browser.setTimeout(later, wait);
            if (callNow) {
                func.apply(context, args);
            }
        },
    }[funcName];
}

/**
 * Returns a function which returns a Promise, that, as long as it continues
 * to be invoked, will not be triggered. The function (func) will be called
 * after it stops being called for N milliseconds and the Promise will be resolved.
 *
 * @param {Function} func
 * @param {number} wait
 * @returns {Function}
 */
export function debouncePromise(func, wait) {
    let resolver;
    const funcName = func.name ? func.name + " (promise)" : "promise";
    const obj = {
        [funcName]: (...args) => {
            func.apply(this, args);
            resolver();
        },
    };
    const debouncedFunc = debounce(obj[funcName], wait);
    return {
        [funcName](...args) {
            return new Promise((resolve) => {
                resolver = resolve;
                debouncedFunc.apply(this, args);
            });
        },
    }[funcName];
}

/**
 * Returns a function, that, as long as it continues to be invoked, will be
 * triggered every N milliseconds.
 *
 * @param {Function} func
 * @param {number} wait
 * @returns {Function}
 */
export function throttle(func, wait) {
    let waiting = false;
    const funcName = func.name ? func.name + " (throttle)" : "throttle";
    return {
        [funcName](...args) {
            const context = this;
            if (!waiting) {
                waiting = true;
                browser.setTimeout(function () {
                    waiting = false;
                    func.call(context, ...args);
                }, wait);
            }
        },
    }[funcName];
}
