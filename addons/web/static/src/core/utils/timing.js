/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { onWillUnmount, useComponent } from "@odoo/owl";

/**
 * Creates and returns a new debounced version of the passed function (func)
 * which will postpone its execution until after 'delay' milliseconds
 * have elapsed since the last time it was invoked. The debounced function
 * will return a Promise that will be resolved when the function (func)
 * has been fully executed. If `immediate` is passed, trigger the function
 * on the leading edge, instead of the trailing.
 *
 * @template {Function} T the return type of the original function
 * @param {T} func the function to debounce
 * @param {number | "animationFrame"} delay how long should elapse before the function
 *      is called. If 'animationFrame' is given instead of a number, 'requestAnimationFrame'
 *      will be used instead of 'setTimeout'.
 * @param {boolean} [immediate=false] whether the function should be called on
 *      the leading edge instead of the trailing edge.
 * @returns {T & { cancel: () => void }} the debounced function
 */
export function debounce(func, delay, immediate = false) {
    let handle;
    const funcName = func.name ? func.name + " (debounce)" : "debounce";
    const useAnimationFrame = delay === "animationFrame";
    const setFnName = useAnimationFrame ? "requestAnimationFrame" : "setTimeout";
    const clearFnName = useAnimationFrame ? "cancelAnimationFrame" : "clearTimeout";
    return Object.assign(
        {
            /** @type {any} */
            [funcName](...args) {
                return new Promise((resolve) => {
                    const callNow = immediate && !handle;
                    browser[clearFnName](handle);
                    handle = browser[setFnName](() => {
                        handle = null;
                        if (!immediate) {
                            Promise.resolve(func.apply(this, args)).then(resolve);
                        }
                    }, delay);
                    if (callNow) {
                        Promise.resolve(func.apply(this, args)).then(resolve);
                    }
                });
            },
        }[funcName],
        {
            cancel() {
                browser[clearFnName](handle);
            },
        }
    );
}

/**
 * Function that calls recursively a request to an animation frame.
 * Useful to call a function repetitively, until asked to stop, that needs constant rerendering.
 * The provided callback gets as argument the time the last frame took.
 * @param {(deltaTime: number) => void} callback
 * @returns {() => void} stop function
 */
export function setRecurringAnimationFrame(callback) {
    const handler = (timestamp) => {
        callback(timestamp - lastTimestamp);
        lastTimestamp = timestamp;
        handle = browser.requestAnimationFrame(handler);
    };

    const stop = () => {
        browser.cancelAnimationFrame(handle);
    };

    let lastTimestamp = browser.performance.now();
    let handle = browser.requestAnimationFrame(handler);

    return stop;
}

/**
 * Creates a version of the function where only the last call between two
 * animation frames is executed before the browser's next repaint. This
 * effectively throttles the function to the display's refresh rate.
 * Note that the throttled function can be any callback. It is not
 * specifically an event handler, no assumption is made about its
 * signature.
 * NB: The first call is always called immediately (leading edge).
 *
 * @template {Function} T
 * @param {T} func the function to throttle
 * @returns {T & { cancel: () => void }} the throttled function
 */
export function throttleForAnimation(func) {
    let handle = null;
    const calls = new Set();
    const funcName = func.name ? `${func.name} (throttleForAnimation)` : "throttleForAnimation";
    const pending = () => {
        if (calls.size) {
            handle = browser.requestAnimationFrame(pending);
            const { args, resolve } = [...calls].pop();
            calls.clear();
            Promise.resolve(func.apply(this, args)).then(resolve);
        } else {
            handle = null;
        }
    };
    return Object.assign(
        {
            /** @type {any} */
            [funcName](...args) {
                return new Promise((resolve) => {
                    const isNew = handle === null;
                    if (isNew) {
                        handle = browser.requestAnimationFrame(pending);
                        Promise.resolve(func.apply(this, args)).then(resolve);
                    } else {
                        calls.add({ args, resolve });
                    }
                });
            },
        }[funcName],
        {
            cancel() {
                browser.cancelAnimationFrame(handle);
                calls.clear();
                handle = null;
            },
        }
    );
}

// ----------------------------------- HOOKS -----------------------------------

/**
 * Hook that returns a debounced version of the given function, and cancels
 * the potential pending execution on willUnmount.
 * @see debounce
 * @template {Function} T
 * @param {T} callback
 * @param {number | "animationFrame"} delay
 * @param {boolean} [immediate=false] whether the function should be called on
 *      the leading edge instead of the trailing edge.
 * @returns {T & { cancel: () => void }}
 */
export function useDebounced(callback, delay, immediate = false) {
    const component = useComponent();
    const debounced = debounce(callback.bind(component), delay, immediate);
    onWillUnmount(() => debounced.cancel());
    return debounced;
}

/**
 * Hook that returns a throttled for animation version of the given function,
 * and cancels the potential pending execution on willUnmount.
 * @see throttleForAnimation
 * @template {Function} T
 * @param {T} func the function to throttle
 * @returns {T & { cancel: () => void }} the throttled function
 */
export function useThrottleForAnimation(func) {
    const component = useComponent();
    const throttledForAnimation = throttleForAnimation(func.bind(component));
    onWillUnmount(() => throttledForAnimation.cancel());
    return throttledForAnimation;
}
