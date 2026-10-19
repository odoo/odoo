import { computed, onWillDestroy, signal } from "@odoo/owl";
import { clamp } from "@web/core/utils/numbers";

/**
 * Creates a batched version of a callback so that all calls to it in the same
 * time frame will only call the original callback once.
 * @template {(...args: any[]) => any} T
 * @param {T} func the callback to batch
 * @param {() => Promise<any>} [synchronize] decides the granularity of the batch (default: 1 microtick)
 * @returns {T} a batched version of the original callback
 */
export function batched(func, synchronize = () => Promise.resolve()) {
    const funcName = func.name ? func.name + " (batched)" : "batched";
    let scheduled = false;
    return {
        /** @type {T} */
        async [funcName](...args) {
            if (!scheduled) {
                scheduled = true;
                await synchronize();
                scheduled = false;
                // Note: all 'func' calls keep 'this' in case the function is assigned
                // and called from a class instance.
                func.apply(this, args);
            }
        },
    }[funcName];
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
 * @template {(...args: any[]) => any} T the return type of the original function
 * @param {T} func the function to debounce
 * @param {number | "animationFrame"} delay how long should elapse before the function
 *  is called. If 'animationFrame' is given instead of a number, 'requestAnimationFrame'
 *  will be used instead of 'setTimeout'.
 * @param {boolean | {
 *  leading?: boolean;
 *  trailing?: boolean;
 * }} [options]
 * @returns the debounced function
 */
export function debounce(func, delay, options) {
    function cancel(execNow = false) {
        clearFn(handle);
        if (execNow && lastArgs) {
            func.apply(this, lastArgs);
        }
    }

    const funcName = func.name ? func.name + " (debounce)" : "debounce";
    const useAnimationFrame = delay === "animationFrame";
    const setFn = useAnimationFrame ? requestAnimationFrame : setTimeout;
    const clearFn = useAnimationFrame ? cancelAnimationFrame : clearTimeout;
    let handle = null;
    /** @type {Parameters<T> | null} */
    let lastArgs = null;
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
            /** @type {T} */
            [funcName](...args) {
                return new Promise((resolve) => {
                    if (leading && !handle) {
                        // Note: all 'func' calls keep 'this' in case the function
                        // is assigned and called from a class instance.
                        Promise.resolve(func.apply(this, args)).then(resolve);
                    } else {
                        lastArgs = args;
                    }
                    clearFn(handle);
                    handle = setFn(() => {
                        handle = null;
                        if (trailing && lastArgs) {
                            Promise.resolve(func.apply(this, lastArgs)).then(resolve);
                            lastArgs = null;
                        }
                    }, delay);
                });
            },
        }[funcName],
        { cancel }
    );
}

/**
 * Function that calls recursively a request to an animation frame.
 * Useful to call a function repetitively, until asked to stop, that needs constant rerendering.
 * The provided callback gets as argument the time the last frame took.
 * @param {(deltaTime: number) => void} callback
 * @returns stop function
 */
export function setRecurringAnimationFrame(callback) {
    /**
     * @param {number} timestamp
     */
    function handler(timestamp) {
        callback(timestamp - lastTimestamp);
        lastTimestamp = timestamp;
        handle = requestAnimationFrame(handler);
    }

    function stop() {
        cancelAnimationFrame(handle);
    }

    let lastTimestamp = performance.now();
    let handle = requestAnimationFrame(handler);

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
 * @template {(...args: any[]) => any} T
 * @param {T} func the function to throttle
 * @returns the throttled function
 */
export function throttleForAnimation(func) {
    function cancel() {
        cancelAnimationFrame(handle);
        handle = null;
        lastArgsAndResolve = null;
    }

    function pending() {
        if (lastArgsAndResolve) {
            handle = requestAnimationFrame(pending.bind(this));
            const [lastArgs, resolve] = lastArgsAndResolve;
            Promise.resolve(func.apply(this, lastArgs)).then(resolve);
            lastArgsAndResolve = null;
        } else {
            handle = null;
        }
    }

    const funcName = func.name ? `${func.name} (throttleForAnimation)` : "throttleForAnimation";
    let handle = null;
    /** @type {[args: Parameters<T>, resolve: () => void] | null} */
    let lastArgsAndResolve = null;

    return Object.assign(
        {
            /** @type {T} */
            [funcName](...args) {
                return new Promise((resolve) => {
                    if (handle) {
                        lastArgsAndResolve = [args, resolve];
                    } else {
                        // Note: all 'func' calls keep 'this' in case the function
                        // is assigned and called from a class instance.
                        handle = requestAnimationFrame(pending.bind(this));
                        Promise.resolve(func.apply(this, args)).then(resolve);
                    }
                });
            },
        }[funcName],
        { cancel }
    );
}

// ----------------------------------- HOOKS -----------------------------------

/**
 * Hook that returns a debounced version of the given function, and cancels
 * the potential pending execution on willUnmount.
 * @see debounce
 * @template {(...args: any[]) => any} T
 * @param {T} callback
 * @param {number | "animationFrame"} delay
 * @param {Object} [options]
 * @param {string} [options.execBeforeUnmount=false] executes the callback if the debounced function
 *      has been called and not resolved before destroying the component.
 * @param {boolean} [options.immediate=false] whether the function should be called on
 *      the leading edge of the timeout.
 * @param {boolean} [options.trailing=!options.immediate] whether the function should be called on
 *      the trailing edge of the timeout.
 */
export function useDebounced(
    callback,
    delay,
    { execBeforeUnmount = false, immediate = false, trailing = !immediate } = {}
) {
    const debounced = debounce(callback, delay, { leading: immediate, trailing });
    onWillDestroy(() => debounced.cancel(execBeforeUnmount));
    return debounced;
}

/**
 * Hook that returns a throttled for animation version of the given function,
 * and cancels the potential pending execution on willUnmount.
 * @see throttleForAnimation
 * @template {(...args: any[]) => any} T
 * @param {T} func the function to throttle
 */
export function useThrottleForAnimation(func) {
    const throttledForAnimation = throttleForAnimation(func);
    onWillDestroy(throttledForAnimation.cancel);
    return throttledForAnimation;
}

/**
 * Hook that animates a progress value from 0 to 1 over a given duration.
 * The animation starts immediately and is automatically stopped when the
 * component is destroyed.
 * @param {number} duration total duration of the timer in milliseconds
 * @returns
 *  - `progress`: reactive computed value in [0, 1] tracking the elapsed fraction of the duration
 *  - `stop`: cancels the running animation frame
 *  - `reset`: restarts the timer from the beginning
 *  - `resume`: resumes the timer from the current progress
 */
export function useTimer(duration) {
    const progress = signal(0);
    let start = Date.now();
    let handle = null;

    const animate = () => {
        handle = requestAnimationFrame(() => {
            const elapsed = Date.now() - start;
            progress.set(clamp(elapsed / duration, 0, 1));
            if (elapsed < duration) {
                animate();
            }
        });
    };

    const stop = () => cancelAnimationFrame(handle);

    const reset = () => {
        stop();
        start = Date.now();
        animate();
    };

    const resume = () => {
        stop();
        start = Date.now() - progress() * duration;
        animate();
    };

    animate();

    onWillDestroy(stop);

    return {
        progress: computed(progress),
        stop,
        reset,
        resume,
    };
}
