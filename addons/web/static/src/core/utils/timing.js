import { browser } from "@web/core/browser/browser";
import { onWillUnmount, useComponent } from "@odoo/owl";

/**
 * Creates a batched version of a callback so that all calls to it in the same
 * time frame will only call the original callback once.
 * @param callback the callback to batch
 * @param synchronize this function decides the granularity of the batch (a microtick by default)
 * @returns a batched version of the original callback
 */
export function batched(callback, synchronize = () => Promise.resolve()) {
    let scheduled = false;
    return async (...args) => {
        if (!scheduled) {
            scheduled = true;
            await synchronize();
            scheduled = false;
            callback(...args);
        }
    };
}

/**
 * Creates and returns a new debounced version of the passed function (func)
 * which will postpone its execution until after 'delay' milliseconds
 * have elapsed since the last time it was invoked. The debounced function
 * will return a Promise that will be resolved when the function (func)
 * has been fully executed.
 *
 * If both `options.trailing` and `options.leading` are true, the function
 * will only be invoked at the trailing edge if the debounced function was
 * called at least once more during the wait time.
 *
 * @template {Function} T the return type of the original function
 * @param {T} func the function to debounce
 * @param {number | "animationFrame"} delay how long should elapse before the function
 *      is called. If 'animationFrame' is given instead of a number, 'requestAnimationFrame'
 *      will be used instead of 'setTimeout'.
 * @param {boolean} [options] if true, equivalent to exclusive leading. If false, equivalent to exclusive trailing.
 * @param {object} [options]
 * @param {boolean} [options.leading=false] whether the function should be invoked at the leading edge of the timeout
 * @param {boolean} [options.trailing=true] whether the function should be invoked at the trailing edge of the timeout
 * @returns {T & { cancel: () => void }} the debounced function
 */
export function debounce(func, delay, options) {
    let handle;
    const funcName = func.name ? func.name + " (debounce)" : "debounce";
    const useAnimationFrame = delay === "animationFrame";
    const setFnName = useAnimationFrame ? "requestAnimationFrame" : "setTimeout";
    const clearFnName = useAnimationFrame ? "cancelAnimationFrame" : "clearTimeout";
    let lastArgs;
    let leading = false;
    let trailing = true;
    if (typeof options === "boolean") {
        leading = options;
        trailing = !options;
    } else if (options) {
        leading = options.leading ?? leading;
        trailing = options.trailing ?? trailing;
    }

    return Object.assign(
        {
            /** @type {any} */
            [funcName](...args) {
                return new Promise((resolve) => {
                    if (leading && !handle) {
                        Promise.resolve(func.apply(this, args)).then(resolve);
                    } else {
                        lastArgs = args;
                    }
                    browser[clearFnName](handle);
                    handle = browser[setFnName](() => {
                        handle = null;
                        if (trailing && lastArgs) {
                            Promise.resolve(func.apply(this, lastArgs)).then(resolve);
                            lastArgs = null;
                        }
                    }, delay);
                });
            },
        }[funcName],
        {
            cancel(execNow = false) {
                browser[clearFnName](handle);
                if (execNow && lastArgs) {
                    func.apply(this, lastArgs);
                }
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
 * @param {Object} [options]
 * @param {string} [options.execBeforeUnmount=false] executes the callback if the debounced function
 *      has been called and not resolved before destroying the component.
 * @param {boolean} [options.immediate=false] whether the function should be called on
 *      the leading edge of the timeout.
 * @param {boolean} [options.trailing=!options.immediate] whether the function should be called on
 *      the trailing edge of the timeout.
 * @returns {T & { cancel: () => void }}
 */
export function useDebounced(
    callback,
    delay,
    { execBeforeUnmount = false, immediate = false, trailing = !immediate } = {}
) {
    const component = useComponent();
    const debounced = debounce(callback.bind(component), delay, { leading: immediate, trailing });
    onWillUnmount(() => debounced.cancel(execBeforeUnmount));
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
