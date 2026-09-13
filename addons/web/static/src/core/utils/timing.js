// @ts-check
/** @odoo-module native */

import { onWillUnmount, useComponent } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { makeLogger } from "@web/core/debug/debug_logger";

const log = makeLogger("web.timing");

/**
 * @template {any[]} Args
 * @template Result
 * @param {(...args: Args) => Result} callback
 * @param {() => Promise<void>} [synchronize]
 * @returns {(...args: Args) => Promise<Awaited<Result>>}
 */
export function batched(callback, synchronize = () => Promise.resolve()) {
    let scheduled = false;
    /** @type {Args} */
    let lastArgs;
    /** @type {{ resolve: (value: any) => void, reject: (reason?: any) => void }[]} */
    let awaiters = [];
    return (/** @type {Args} */ ...args) => {
        lastArgs = args;
        const { promise, resolve, reject } = Promise.withResolvers();
        awaiters.push({ resolve, reject });
        if (!scheduled) {
            scheduled = true;
            const settlers = awaiters;
            log.pipeline("batch.schedule");
            (async () => {
                try {
                    await synchronize();
                    scheduled = false;
                    awaiters = [];
                    const result = await callback(...lastArgs);
                    log.pipeline("batch.resolve", () => ({ callers: settlers.length }));
                    for (const settler of settlers) {
                        settler.resolve(result);
                    }
                } catch (error) {
                    // A callback may already have scheduled another batch.
                    if (awaiters === settlers) {
                        scheduled = false;
                        awaiters = [];
                    }
                    console.error(error);
                    log.pipeline("batch.reject", () => ({
                        callers: settlers.length,
                        error,
                    }));
                    for (const settler of settlers) {
                        settler.reject(error);
                    }
                }
            })();
        }
        return /** @type {any} */ (promise);
    };
}

export const INPUT_DEBOUNCE_DELAY = 250;

/**
 * @param {Function} func
 * @param {any} self
 * @param {any[]} args
 * @param {{ resolve: Function, reject: Function }[]} awaiters
 */
function executeAndSettle(func, self, args, awaiters) {
    let result;
    try {
        result = func.apply(self, args);
    } catch (error) {
        for (const { reject } of awaiters) {
            reject(error);
        }
        return;
    }
    Promise.resolve(result).then(
        (value) => {
            for (const { resolve } of awaiters) {
                resolve(value);
            }
        },
        (error) => {
            for (const { reject } of awaiters) {
                reject(error);
            }
        },
    );
}

/**
 * @param {boolean | {leading?: boolean, trailing?: boolean}} [options]
 * @returns {{ leading: boolean, trailing: boolean }}
 */
function debounceEdges(options) {
    if (typeof options === "boolean") {
        return { leading: options, trailing: !options };
    }
    return { leading: options?.leading ?? false, trailing: options?.trailing ?? true };
}

/**
 * Pending calls resolve to undefined when cancelled or when trailing execution is disabled.
 * @template {(...args: any[]) => any} T
 * @param {T} func
 * @param {number | "animationFrame" | (() => number)} [delay]
 * @param {boolean | {leading?: boolean, trailing?: boolean}} [options]
 * @returns {((this: ThisParameterType<T>, ...args: Parameters<T>) => Promise<Awaited<ReturnType<T>> | undefined>) & { cancel: (execNow?: boolean) => void }}
 */
export function debounce(func, delay, options) {
    /** @type {any} */
    let handle = null;
    const funcName = func.name ? `${func.name} (debounce)` : "debounce";
    const getDelay = typeof delay === "function" ? delay : () => delay;
    const useAnimationFrame = delay === "animationFrame";
    const setFnName = useAnimationFrame ? "requestAnimationFrame" : "setTimeout";
    const clearFnName = useAnimationFrame ? "cancelAnimationFrame" : "clearTimeout";
    /** @type {any[] | null} */
    let lastArgs = null;
    const { leading, trailing } = debounceEdges(options);

    /** @type {any} */
    let lastSelf = null;
    /** @type {{ resolve: Function, reject: Function }[]} */
    let pending = [];

    /** @param {boolean} execute */
    function settlePending(execute) {
        const awaiters = pending;
        const args = lastArgs;
        const self = lastSelf;
        // Release the old invocation before user code can enqueue another one.
        pending = [];
        lastArgs = null;
        lastSelf = null;
        log.pipeline("debounce.settle", () => ({
            name: funcName,
            callers: awaiters.length,
            execute: Boolean(execute && trailing && args),
        }));
        if (execute && trailing && args) {
            executeAndSettle(func, self, args, awaiters);
        } else {
            for (const { resolve } of awaiters) {
                resolve(undefined);
            }
        }
    }

    return Object.assign(
        {
            /** @type {any} */
            [funcName](/** @type {any[]} */ ...args) {
                return new Promise((resolve, reject) => {
                    const timeout = getDelay();
                    const callLeading = leading && handle === null;
                    if (!callLeading) {
                        pending.push({ resolve, reject });
                        lastArgs = args;
                        lastSelf = this;
                    }
                    browser[clearFnName](handle);
                    handle = /** @type {any} */ (browser)[setFnName](() => {
                        handle = null;
                        settlePending(true);
                    }, timeout);
                    if (callLeading) {
                        executeAndSettle(func, this, args, [{ resolve, reject }]);
                    }
                });
            },
        }[funcName],
        {
            cancel(execNow = false) {
                browser[clearFnName](handle);
                handle = null;
                settlePending(execNow);
            },
        },
    );
}

/**
 * @param {(deltaTime: number) => void} callback
 * @returns {() => void}
 */
export function setRecurringAnimationFrame(callback) {
    let stopped = false;
    const handler = (/** @type {number} */ timestamp) => {
        callback(timestamp - lastTimestamp);
        lastTimestamp = timestamp;
        if (!stopped) {
            handle = browser.requestAnimationFrame(handler);
        }
    };

    const stop = () => {
        stopped = true;
        browser.cancelAnimationFrame(handle);
    };

    let lastTimestamp = browser.performance.now();
    let handle = browser.requestAnimationFrame(handler);

    return stop;
}

/**
 * Calls resolve to the callback result, or undefined when superseded or cancelled.
 * @template {(...args: any[]) => any} T
 * @param {T} func
 * @returns {((this: ThisParameterType<T>, ...args: Parameters<T>) => Promise<Awaited<ReturnType<T>> | undefined>) & { cancel: () => void }}
 */
export function throttleForAnimation(func) {
    /** @type {any} */
    let handle = null;
    /** @type {{ args: any[], resolve: (value: any) => any, reject: (reason?: any) => any } | null} */
    let lastCall = null;
    const funcName = func.name
        ? `${func.name} (throttleForAnimation)`
        : "throttleForAnimation";
    /** @type {any} */
    let self;
    const pending = () => {
        if (lastCall) {
            handle = browser.requestAnimationFrame(pending);
            const { args, resolve, reject } = lastCall;
            lastCall = null;
            try {
                Promise.resolve(func.apply(self, args)).then(resolve, reject);
            } catch (error) {
                reject(error);
            }
        } else {
            handle = null;
        }
    };
    return Object.assign(
        {
            /** @type {any} */
            [funcName](/** @type {any[]} */ ...args) {
                self = this;
                return new Promise((resolve, reject) => {
                    const isNew = handle === null;
                    if (isNew) {
                        handle = browser.requestAnimationFrame(pending);
                        try {
                            Promise.resolve(func.apply(this, args)).then(
                                resolve,
                                reject,
                            );
                        } catch (error) {
                            reject(error);
                        }
                    } else {
                        if (lastCall) {
                            lastCall.resolve(undefined);
                        }
                        lastCall = { args, resolve, reject };
                    }
                });
            },
        }[funcName],
        {
            cancel() {
                browser.cancelAnimationFrame(handle);
                if (lastCall) {
                    lastCall.resolve(undefined);
                    lastCall = null;
                }
                handle = null;
            },
        },
    );
}

/**
 * @template {(...args: any[]) => any} T
 * @param {T} callback
 * @param {number | "animationFrame" | (() => number)} delay
 * @param {{execBeforeUnmount?: boolean, immediate?: boolean, trailing?: boolean}} [options]
 * @returns {((...args: Parameters<T>) => Promise<Awaited<ReturnType<T>> | undefined>) & { cancel: (execNow?: boolean) => void }}
 */
export function useDebounced(
    callback,
    delay,
    { execBeforeUnmount = false, immediate = false, trailing = !immediate } = {},
) {
    const component = useComponent();
    /** @type {(...args: Parameters<T>) => ReturnType<T>} */
    const invoke = (...args) => callback.apply(component, args);
    const debounced = debounce(invoke, delay, {
        leading: immediate,
        trailing,
    });
    onWillUnmount(() => debounced.cancel(execBeforeUnmount));
    return debounced;
}

/**
 * The component supplies the callback receiver; callers only supply its arguments.
 * @template {(...args: any[]) => any} T
 * @param {T} func
 * @returns {((...args: Parameters<T>) => Promise<Awaited<ReturnType<T>> | undefined>) & { cancel: () => void }}
 */
export function useThrottleForAnimation(func) {
    const component = useComponent();
    /** @type {(...args: Parameters<T>) => ReturnType<T>} */
    const bound = func.bind(component);
    const throttledForAnimation = throttleForAnimation(bound);
    onWillUnmount(() => throttledForAnimation.cancel());
    return throttledForAnimation;
}
