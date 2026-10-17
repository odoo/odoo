/** @odoo-module */

import { isInstanceOf } from "../hoot_dom_utils";

/**
 * @typedef {{
 *  animationFrame?: boolean;
 *  blockTimers?: boolean;
 * }} AdvanceTimeOptions
 *
 * @typedef {"animation" | "interval" | "timeout"} TimerType
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
    Object: { entries: $entries },
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
 * Starts a timer, tracked until it is stopped (or run, except for intervals) so
 * that {@link _discardTimers} can cancel it.
 *
 * Mocked timers are also registered in `timers`, to be run by time helpers such
 * as {@link advanceTime}, and are given a dummy ID instead of being actually
 * started while time is frozen.
 *
 * @param {TimerType} type
 * @param {(...args: any[]) => any} callback animation callbacks receive the
 *  current time, other callbacks receive the given `args`
 * @param {number} ms
 * @param {boolean} [mocked=false]
 * @param {any[]} [args=[]]
 * @returns {number}
 */
function startTimer(type, callback, ms, mocked = false, args = []) {
    function handler() {
        if (!allowTimers || type !== "interval") {
            stopTimer(type, id);
        } else if (timerValues) {
            timerValues[1] = $max(now(), timerValues[1] + ms);
        }
        return type === "animation" ? callback(now()) : callback(...args);
    }

    let id;
    let timerValues;
    if (mocked && frozen) {
        id = nextDummyId++;
    } else {
        const { start } = NATIVE_TIMERS[type];
        id = start(handler, ms);
        nativeIds[type].add(id);
    }
    if (mocked) {
        timerValues = [handler, now(), ms];
        timers.set(ID_PREFIX[type] + id, timerValues);
    }
    return id;
}

/**
 * Cancels the given timer (if not run yet), and stops tracking it.
 *
 * @param {TimerType} type
 * @param {number} id
 */
function stopTimer(type, id) {
    if (nativeIds[type].delete(id)) {
        const { stop } = NATIVE_TIMERS[type];
        stop(id);
    }
    timers.delete(ID_PREFIX[type] + id);
}

class HootTimingError extends Error {
    name = "HootTimingError";
}

const DEFAULT_FRAME_RATE = 60;
const DEFAULT_WAIT_TIMEOUT = 3_000;

const ID_PREFIX = {
    animation: "a_",
    interval: "i_",
    timeout: "t_",
};

/** @type {Record<TimerType, { start: Function, stop: Function }>} */
const NATIVE_TIMERS = {
    animation: { start: requestAnimationFrame, stop: cancelAnimationFrame },
    interval: { start: setInterval, stop: clearInterval },
    timeout: { start: setTimeout, stop: clearTimeout },
};

/**
 * IDs of the native timers started (and not yet stopped) by Hoot-DOM.
 *
 * @type {Record<TimerType, Set<number>>}
 */
const nativeIds = {
    animation: new Set(),
    interval: new Set(),
    timeout: new Set(),
};
/** @type {Map<string, [() => any, number, number]>} */
const timers = new Map();

let allowTimers = false;
let defaultWaitTimeout = DEFAULT_WAIT_TIMEOUT;
let frozen = false;
let frameDelay = 1000 / DEFAULT_FRAME_RATE;
// Native timer IDs are positive 32-bit integers: dummy IDs must never match one
let nextDummyId = 2 ** 31;
let timeOffset = 0;

//-----------------------------------------------------------------------------
// Internal exports (inside Hoot/Hoot-DOM)
//-----------------------------------------------------------------------------

export function _cleanupTime() {
    allowTimers = false;
    frozen = false;

    _discardTimers();

    // Wait for remaining async code to run
    return delay();
}

/**
 * Stops **all** pending timers: they will neither resolve nor
 * reject, so that code awaiting them is never resumed.
 *
 * This prevents a wait started during a test from resuming its caller (or
 * rejecting) after that test has ended.
 */
export function _discardTimers() {
    for (const [type, ids] of $entries(nativeIds)) {
        const { stop } = NATIVE_TIMERS[type];
        for (const id of ids) {
            stop(id);
        }
        ids.clear();
    }
    timers.clear();
}

export function _getDefaultWaitTimeout() {
    return defaultWaitTimeout;
}

export function _getTimeOffset() {
    return timeOffset;
}

export function _isTimeFrozen() {
    return frozen;
}

/** @type {typeof cancelAnimationFrame} */
export function _mockedCancelAnimationFrame(handle) {
    stopTimer("animation", handle);
}

/** @type {typeof clearInterval} */
export function _mockedClearInterval(intervalId) {
    stopTimer("interval", intervalId);
}

/** @type {typeof clearTimeout} */
export function _mockedClearTimeout(timeoutId) {
    stopTimer("timeout", timeoutId);
}

/** @type {typeof requestAnimationFrame} */
export function _mockedRequestAnimationFrame(callback) {
    return allowTimers ? startTimer("animation", callback, frameDelay, true) : 0;
}

/** @type {typeof setInterval} */
export function _mockedSetInterval(handler, timeout, ...args) {
    return allowTimers ? startTimer("interval", handler, parseNat(timeout), true, args) : 0;
}

/** @type {typeof setTimeout} */
export function _mockedSetTimeout(handler, timeout, ...args) {
    return allowTimers ? startTimer("timeout", handler, parseNat(timeout), true, args) : 0;
}

export function _resetTimeOffset() {
    timeOffset = 0;
}

/**
 * Sets the default timeout (in milliseconds) of {@link waitUntil} and derived
 * helpers. Omitting it resets the timeout to its original value (3 seconds).
 *
 * @param {number} [timeout]
 */
export function _setDefaultWaitTimeout(timeout) {
    defaultWaitTimeout = timeout ? parseNat(timeout) : DEFAULT_WAIT_TIMEOUT;
}

/**
 * Sets the current frame rate (in fps) used by animation frames (default to 60fps).
 *
 * @param {number} frameRate
 */
export function _setFrameRate(frameRate) {
    frameRate = parseNat(frameRate);
    if (frameRate < 1 || frameRate > 1000) {
        throw new HootTimingError("frame rate must be an number between 1 and 1000");
    }
    frameDelay = 1000 / frameRate;
}

export function _setupTime() {
    allowTimers = true;

    _discardTimers();
}

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
    return new Promise((resolve) =>
        startTimer("animation", () => startTimer("timeout", resolve, 0), frameDelay)
    );
}

/**
 * Cancels all current timeouts, intervals and animations.
 */
export function cancelAllTimers() {
    for (const internalId of timers.keys()) {
        for (const [type, prefix] of $entries(ID_PREFIX)) {
            if (internalId.startsWith(prefix)) {
                stopTimer(type, Number(internalId.slice(prefix.length)));
                break;
            }
        }
    }
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
    return new Promise((resolve) => startTimer("timeout", resolve, parseNat(duration)));
}

export function freezeTime() {
    frozen = true;
}

export function unfreezeTime() {
    frozen = false;
}

/**
 * Returns a promise resolved after the next microtask tick.
 *
 * @returns {Promise<void>}
 */
export function microTick() {
    return new Promise(queueMicrotask);
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
 * The promise automatically rejects after a given `timeout` (defaults to 3 seconds,
 * see {@link DEFAULT_WAIT_TIMEOUT}).
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

    const timeout = $floor(options?.timeout ?? defaultWaitTimeout);
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
                handle = startTimer("animation", runCheck, frameDelay);
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

        handle = startTimer("animation", runCheck, frameDelay);
    }).finally(() => {
        stopTimer("animation", handle);
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
