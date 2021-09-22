/** @odoo-module **/

import { browser } from "../browser/browser";

/**
 * Creates and returns a new debounced version of the passed function (func)
 * which will postpone its execution until after wait milliseconds
 * have elapsed since the last time it was invoked. The debounced function
 * will return a Promise that will be resolved when the function (func)
 * has been fully executed. If `immediate` is passed, trigger the function
 * on the leading edge, instead of the trailing.
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
            let resolve;
            const prom = new Promise((r) => {
                resolve = r;
            });
            function later() {
                if (!immediate) {
                    Promise.resolve(func.apply(context, args)).then(resolve);
                }
            }
            const callNow = immediate && !timeout;
            browser.clearTimeout(timeout);
            timeout = browser.setTimeout(later, wait);
            if (callNow) {
                Promise.resolve(func.apply(context, args)).then(resolve);
            }
            return prom;
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
