/** @odoo-module **/

import { browser } from "../browser/browser";

/**
 * Creates a version of the function where only the last call between two
 * animation frames is executed before the browser's next repaint. This
 * effectively throttles the function to the display's refresh rate.
 *
 * @param {Function} func the function to throttle
 * @returns {{ (...args): void, cancel: () => void }} the throttled function
 */
export function throttleForAnimation(func) {
    let handle = null;
    const funcName = func.name ? `${func.name} (throttleForAnimation)` : "throttleForAnimation";
    return Object.assign(
        {
            [funcName](...args) {
                browser.cancelAnimationFrame(handle);
                handle = browser.requestAnimationFrame(() => {
                    handle = null;
                    func.call(this, ...args);
                });
            },
        }[funcName],
        {
            cancel() {
                browser.cancelAnimationFrame(handle);
            },
        }
    );
}

/**
 * Creates and returns a new debounced version of the passed function (func)
 * which will postpone its execution until after wait milliseconds
 * have elapsed since the last time it was invoked. The debounced function
 * will return a Promise that will be resolved when the function (func)
 * has been fully executed. If `immediate` is passed, trigger the function
 * on the leading edge, instead of the trailing.
 *
 * @template T the return type of the original function
 * @param {(...args) => T} func the function to debounce
 * @param {number} wait how long should elapse before the function is called
 * @param {boolean} [immediate=false] whether the function should be called on
 *      the leading edge instead of the trailing edge.
 * @returns {{ (...args): Promise<T>, cancel: () => void }} the debounced function
 */
export function debounce(func, wait, immediate = false) {
    let cancelled;
    let timeout;
    const funcName = func.name ? func.name + " (debounce)" : "debounce";
    return Object.assign(
        {
            [funcName](...args) {
                const context = this;
                let resolve;
                const prom = new Promise((r) => {
                    resolve = r;
                });
                function later() {
                    if (!immediate && !cancelled) {
                        Promise.resolve(func.apply(context, args)).then(resolve);
                    }
                }
                const callNow = immediate && !timeout && !cancelled;
                browser.clearTimeout(timeout);
                timeout = browser.setTimeout(later, wait);
                if (callNow) {
                    Promise.resolve(func.apply(context, args)).then(resolve);
                }
                return prom;
            },
        }[funcName],
        {
            cancel() {
                cancelled = true;
                browser.clearTimeout(timeout);
            },
        }
    );
}

/**
 * Returns a function, that, as long as it continues to be invoked, will be
 * triggered every N milliseconds.
 *
 * @deprecated this function has behaviour that is unexpected considering its
 *      name, prefer _.throttle until this function is rewritten
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
