/** @odoo-module */

import { isInstanceOf } from "../hoot_dom_utils";

/**
 * @typedef {{
 *  animationFrame?: boolean;
 *  blockTimers?: boolean;
 * }} AdvanceTimeOptions
 *
 * @typedef {{
 *  message?: string | () => string;
 *  timeout?: number;
 * }} WaitOptions
 */

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const {
    cancelAnimationFrame,
    clearInterval,
    clearTimeout,
    Error,
    Math: { ceil: $ceil, floor: $floor, max: $max, min: $min },
    Number,
    performance,
    Promise,
    requestAnimationFrame,
    setInterval,
    setTimeout,
} = globalThis;
/** @type {Performance["now"]} */
const $performanceNow = performance.now.bind(performance);

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * @param {number} id
 */
function animationToId(id) {
    return ID_PREFIX.animation + String(id);
}

function getNextTimerValues() {
    /** @type {[number, () => any, string] | null} */
    let timerValues = null;
    for (const [internalId, [callback, init, delay]] of timers.entries()) {
        const timeout = init + delay;
        if (!timerValues || timeout < timerValues[0]) {
            timerValues = [timeout, callback, internalId];
        }
    }
    return timerValues;
}

/**
 * @param {string} id
 */
function idToAnimation(id) {
    return Number(id.slice(ID_PREFIX.animation.length));
}

/**
 * @param {string} id
 */
function idToInterval(id) {
    return Number(id.slice(ID_PREFIX.interval.length));
}

/**
 * @param {string} id
 */
function idToTimeout(id) {
    return Number(id.slice(ID_PREFIX.timeout.length));
}

/**
 * @param {number} id
 */
function intervalToId(id) {
    return ID_PREFIX.interval + String(id);
}

/**
 * Converts a given value to a **natural number** (or 0 if failing to do so).
 *
 * @param {unknown} value
 */
function parseNat(value) {
    return $max($floor(Number(value)), 0) || 0;
}

function now() {
    return (frozen ? 0 : $performanceNow()) + timeOffset;
}

/**
 * @param {number} id
 */
function timeoutToId(id) {
    return ID_PREFIX.timeout + String(id);
}

class HootTimingError extends Error {
    name = "HootTimingError";
}

const ID_PREFIX = {
    animation: "a_",
    interval: "i_",
    timeout: "t_",
};

/** @type {Map<string, [() => any, number, number]>} */
const timers = new Map();

let allowTimers = false;
let frozen = false;
let frameDelay = 1000 / 60;
let nextDummyId = 1;
let timeOffset = 0;

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * @param {number} [frameCount]
 * @param {AdvanceTimeOptions} [options]
 */
export function advanceFrame(frameCount, options) {
    return advanceTime(frameDelay * parseNat(frameCount), options);
}

/**
 * Advances the current time by the given amount of milliseconds. This will
 * affect all timeouts, intervals, animations and date objects.
 *
 * It returns a promise resolved after all related callbacks have been executed.
 *
 * @param {number} ms
 * @param {AdvanceTimeOptions} [options]
 * @returns {Promise<number>} time consumed by timers (in ms).
 */
export async function advanceTime(ms, options) {
    ms = parseNat(ms);

    if (options?.blockTimers) {
        allowTimers = false;
    }

    const targetTime = now() + ms;
    let remaining = ms;
    /** @type {ReturnType<typeof getNextTimerValues>} */
    let timerValues;
    while ((timerValues = getNextTimerValues()) && timerValues[0] <= targetTime) {
        const [timeout, handler, id] = timerValues;
        const diff = timeout - now();
        if (diff > 0) {
            timeOffset += $min(remaining, diff);
            remaining = $max(remaining - diff, 0);
        }
        if (timers.has(id)) {
            handler(timeout);
        }
    }

    if (remaining > 0) {
        timeOffset += remaining;
    }

    if (options?.animationFrame ?? true) {
        await animationFrame();
    }

    allowTimers = true;

    return ms;
}

/**
 * Returns a promise resolved after the next animation frame, typically allowing
 * Owl components to render.
 *
 * @returns {Promise<void>}
 */
export function animationFrame() {
    return new Promise((resolve) => requestAnimationFrame(() => setTimeout(resolve)));
}

/**
 * Cancels all current timeouts, intervals and animations.
 */
export function cancelAllTimers() {
    for (const id of timers.keys()) {
        if (id.startsWith(ID_PREFIX.animation)) {
            globalThis.cancelAnimationFrame(idToAnimation(id));
        } else if (id.startsWith(ID_PREFIX.interval)) {
            globalThis.clearInterval(idToInterval(id));
        } else if (id.startsWith(ID_PREFIX.timeout)) {
            globalThis.clearTimeout(idToTimeout(id));
        }
    }
}

export function cleanupTime() {
    allowTimers = false;
    frozen = false;

    cancelAllTimers();

    // Wait for remaining async code to run
    return delay();
}

/**
 * Returns a promise resolved after a given amount of milliseconds (default to 0).
 *
 * @param {number} [duration]
 * @returns {Promise<void>}
 * @example
 *  await delay(1000); // waits for 1 second
 */
export function delay(duration) {
    return new Promise((resolve) => setTimeout(resolve, duration));
}

export function freezeTime() {
    frozen = true;
}

export function unfreezeTime() {
    frozen = false;
}

export function getTimeOffset() {
    return timeOffset;
}

export function isTimeFrozen() {
    return frozen;
}

/**
 * Returns a promise resolved after the next microtask tick.
 *
 * @returns {Promise<void>}
 */
export function microTick() {
    return new Promise(queueMicrotask);
}

/** @type {typeof cancelAnimationFrame} */
export function mockedCancelAnimationFrame(handle) {
    if (!frozen) {
        cancelAnimationFrame(handle);
    }
    timers.delete(animationToId(handle));
}

/** @type {typeof clearInterval} */
export function mockedClearInterval(intervalId) {
    if (!frozen) {
        clearInterval(intervalId);
    }
    timers.delete(intervalToId(intervalId));
}

/** @type {typeof clearTimeout} */
export function mockedClearTimeout(timeoutId) {
    if (!frozen) {
        clearTimeout(timeoutId);
    }
    timers.delete(timeoutToId(timeoutId));
}

/** @type {typeof requestAnimationFrame} */
export function mockedRequestAnimationFrame(callback) {
    if (!allowTimers) {
        return 0;
    }

    function handler() {
        mockedCancelAnimationFrame(handle);
        return callback(now());
    }

    const animationValues = [handler, now(), frameDelay];
    const handle = frozen ? nextDummyId++ : requestAnimationFrame(handler);
    const internalId = animationToId(handle);
    timers.set(internalId, animationValues);

    return handle;
}

/** @type {typeof setInterval} */
export function mockedSetInterval(callback, ms, ...args) {
    if (!allowTimers) {
        return 0;
    }

    ms = parseNat(ms);

    function handler() {
        if (allowTimers) {
            intervalValues[1] = $max(now(), intervalValues[1] + ms);
        } else {
            mockedClearInterval(intervalId);
        }
        return callback(...args);
    }

    const intervalValues = [handler, now(), ms];
    const intervalId = frozen ? nextDummyId++ : setInterval(handler, ms);
    const internalId = intervalToId(intervalId);
    timers.set(internalId, intervalValues);

    return intervalId;
}

/** @type {typeof setTimeout} */
export function mockedSetTimeout(callback, ms, ...args) {
    if (!allowTimers) {
        return 0;
    }

    ms = parseNat(ms);

    function handler() {
        mockedClearTimeout(timeoutId);
        return callback(...args);
    }

    const timeoutValues = [handler, now(), ms];
    const timeoutId = frozen ? nextDummyId++ : setTimeout(handler, ms);
    const internalId = timeoutToId(timeoutId);
    timers.set(internalId, timeoutValues);

    return timeoutId;
}

export function resetTimeOffset() {
    timeOffset = 0;
}

/**
 * Calculates the amount of time needed to run all current timeouts, intervals and
 * animations, and then advances the current time by that amount.
 *
 * @see {@link advanceTime}
 * @param {AdvanceTimeOptions} [options]
 * @returns {Promise<number>} time consumed by timers (in ms).
 */
export function runAllTimers(options) {
    if (!timers.size) {
        return 0;
    }

    const endts = $max(...[...timers.values()].map(([, init, delay]) => init + delay));
    return advanceTime($ceil(endts - now()), options);
}

/**
 * Sets the current frame rate (in fps) used by animation frames (default to 60fps).
 *
 * @param {number} frameRate
 */
export function setFrameRate(frameRate) {
    frameRate = parseNat(frameRate);
    if (frameRate < 1 || frameRate > 1000) {
        throw new HootTimingError("frame rate must be an number between 1 and 1000");
    }
    frameDelay = 1000 / frameRate;
}

export function setupTime() {
    allowTimers = true;
}

/**
 * Returns a promise resolved after the next task tick.
 *
 * @returns {Promise<void>}
 */
export function tick() {
    return delay();
}

/**
 * Returns a promise fulfilled when the given `predicate` returns a truthy value,
 * with the value of the promise being the return value of the `predicate`.
 *
 * The `predicate` is run once initially, and then on each animation frame until
 * it succeeds or fail.
 *
 * The promise automatically rejects after a given `timeout` (defaults to 5 seconds).
 *
 * @template T
 * @param {(last: boolean) => T} predicate
 * @param {WaitOptions} [options]
 * @returns {Promise<T>}
 * @example
 *  await waitUntil(() => []); // -> []
 * @example
 *  const button = await waitUntil(() => queryOne("button:visible"));
 *  button.click();
 */
export async function waitUntil(predicate, options) {
    await Promise.resolve();

    // Early check before running the loop
    const result = predicate(false);
    if (result) {
        return result;
    }

    const timeout = $floor(options?.timeout ?? 200);
    const maxFrameCount = $ceil(timeout / frameDelay);
    let frameCount = 0;
    let handle;
    return new Promise((resolve, reject) => {
        function runCheck() {
            const isLast = ++frameCount >= maxFrameCount;
            const result = predicate(isLast);
            if (result) {
                resolve(result);
            } else if (!isLast) {
                handle = requestAnimationFrame(runCheck);
            } else {
                let message =
                    options?.message || `'waitUntil' timed out after %timeout% milliseconds`;
                if (typeof message === "function") {
                    message = message();
                }
                if (isInstanceOf(message, Error)) {
                    reject(message);
                } else {
                    reject(new HootTimingError(message.replace("%timeout%", String(timeout))));
                }
            }
        }

        handle = requestAnimationFrame(runCheck);
    }).finally(() => {
        cancelAnimationFrame(handle);
    });
}

/**
 * Manually resolvable and rejectable promise. It introduces 2 new methods:
 *  - {@link reject} rejects the deferred with the given reason;
 *  - {@link resolve} resolves the deferred with the given value.
 *
 * @template [T=unknown]
 */
export class Deferred extends Promise {
    /** @type {typeof Promise.resolve<T>} */
    _resolve;
    /** @type {typeof Promise.reject<T>} */
    _reject;

    /**
     * @param {(resolve: (value?: T) => any, reject: (reason?: any) => any) => any} [executor]
     */
    constructor(executor) {
        let _resolve, _reject;

        super(function deferredResolver(resolve, reject) {
            _resolve = resolve;
            _reject = reject;
            executor?.(_resolve, _reject);
        });

        this._resolve = _resolve;
        this._reject = _reject;
    }

    /**
     * @param {any} [reason]
     */
    async reject(reason) {
        return this._reject(reason);
    }

    /**
     * @param {T} [value]
     */
    async resolve(value) {
        return this._resolve(value);
    }
}
