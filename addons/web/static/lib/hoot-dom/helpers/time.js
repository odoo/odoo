/** @odoo-module */

import { HootDomError } from "../hoot_dom_utils";

/**
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
const animationToId = (id) => ID_PREFIX.animation + String(id);

const getNextTimerValues = () => {
    /** @type {[number, () => any, string] | null} */
    let timerValues = null;
    for (const [internalId, [callback, init, delay]] of timers.entries()) {
        const timeout = init + delay;
        if (!timerValues || timeout < timerValues[0]) {
            timerValues = [timeout, callback, internalId];
        }
    }
    return timerValues;
};

/**
 * @param {string} id
 */
const idToAnimation = (id) => Number(id.slice(ID_PREFIX.animation.length));

/**
 * @param {string} id
 */
const idToInterval = (id) => Number(id.slice(ID_PREFIX.interval.length));

/**
 * @param {string} id
 */
const idToTimeout = (id) => Number(id.slice(ID_PREFIX.timeout.length));

/**
 * @param {number} id
 */
const intervalToId = (id) => ID_PREFIX.interval + String(id);

const now = () => (freezed ? 0 : $performanceNow()) + timeOffset;

/**
 * @param {number} id
 */
const timeoutToId = (id) => ID_PREFIX.timeout + String(id);

const ID_PREFIX = {
    animation: "a_",
    interval: "i_",
    timeout: "t_",
};

/** @type {Map<string, [() => any, number, number]>} */
const timers = new Map();

let allowTimers = false;
let freezed = false;
let frameDelay = 1000 / 60;
let nextDummyId = 1;
let timeOffset = 0;

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * @param {number} [frameCount]
 */
export function advanceFrame(frameCount) {
    return advanceTime(frameDelay * $max(1, frameCount));
}

/**
 * Advances the current time by the given amount of milliseconds. This will
 * affect all timeouts, intervals, animations and date objects.
 *
 * It returns a promise resolved after all related callbacks have been executed.
 *
 * @param {number} ms
 * @returns {Promise<number>} time consumed by timers (in ms).
 */
export function advanceTime(ms) {
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

    // Waits for callbacks to execute
    return animationFrame().then(() => ms);
}

/**
 * Returns a promise resolved after the next animation frame, typically allowing
 * Owl components to render.
 *
 * @returns {Promise<void>}
 */
export function animationFrame() {
    return new Promise((resolve) => requestAnimationFrame(() => delay().then(resolve)));
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

export async function cleanupTime() {
    allowTimers = false;
    freezed = false;

    cancelAllTimers();

    // Wait for remaining async code to run
    await delay();
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

/**
 * @param {boolean} setFreeze
 */
export function freezeTime(setFreeze) {
    freezed = setFreeze ?? !freezed;
}

export function getTimeOffset() {
    return timeOffset;
}

export function isTimeFreezed() {
    return freezed;
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
    if (!freezed) {
        cancelAnimationFrame(handle);
    }
    timers.delete(animationToId(handle));
}

/** @type {typeof clearInterval} */
export function mockedClearInterval(intervalId) {
    if (!freezed) {
        clearInterval(intervalId);
    }
    timers.delete(intervalToId(intervalId));
}

/** @type {typeof clearTimeout} */
export function mockedClearTimeout(timeoutId) {
    if (!freezed) {
        clearTimeout(timeoutId);
    }
    timers.delete(timeoutToId(timeoutId));
}

/** @type {typeof requestAnimationFrame} */
export function mockedRequestAnimationFrame(callback) {
    if (!allowTimers) {
        return 0;
    }

    const handler = () => {
        mockedCancelAnimationFrame(handle);
        return callback(now());
    };

    const animationValues = [handler, now(), frameDelay];
    const handle = freezed ? nextDummyId++ : requestAnimationFrame(handler);
    const internalId = animationToId(handle);
    timers.set(internalId, animationValues);

    return handle;
}

/** @type {typeof setInterval} */
export function mockedSetInterval(callback, ms, ...args) {
    if (!allowTimers) {
        return 0;
    }

    if (isNaN(ms) || !ms || ms < 0) {
        ms = 0;
    }

    const handler = () => {
        if (allowTimers) {
            intervalValues[1] = Math.max(now(), intervalValues[1] + ms);
        } else {
            mockedClearInterval(intervalId);
        }
        return callback(...args);
    };

    const intervalValues = [handler, now(), ms];
    const intervalId = freezed ? nextDummyId++ : setInterval(handler, ms);
    const internalId = intervalToId(intervalId);
    timers.set(internalId, intervalValues);

    return intervalId;
}

/** @type {typeof setTimeout} */
export function mockedSetTimeout(callback, ms, ...args) {
    if (!allowTimers) {
        return 0;
    }

    if (isNaN(ms) || !ms || ms < 0) {
        ms = 0;
    }

    const handler = () => {
        mockedClearTimeout(timeoutId);
        return callback(...args);
    };

    const timeoutValues = [handler, now(), ms];
    const timeoutId = freezed ? nextDummyId++ : setTimeout(handler, ms);
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
 * @returns {Promise<number>} time consumed by timers (in ms).
 */
export async function runAllTimers() {
    if (!timers.size) {
        return 0;
    }

    const endts = $max(...[...timers.values()].map(([, init, delay]) => init + delay));
    const ms = await advanceTime($ceil(endts - now()));

    return ms;
}

/**
 * Sets the current frame rate (in fps) used by animation frames (default to 60fps).
 *
 * @param {number} frameRate
 */
export function setFrameRate(frameRate) {
    if (!Number.isInteger(frameRate) || frameRate <= 0 || frameRate > 1000) {
        throw new Error("frame rate must be an number between 1 and 1000");
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
 * @param {() => T} predicate
 * @param {WaitOptions} [options]
 * @returns {Promise<T>}
 * @example
 *  await waitUntil(() => []); // -> []
 * @example
 *  const button = await waitUntil(() => queryOne("button:visible"));
 *  button.click();
 */
export function waitUntil(predicate, options) {
    // Early check before running the loop
    const result = predicate();
    if (result) {
        return Promise.resolve().then(() => result);
    }

    const timeout = $floor(options?.timeout ?? 200);
    let handle;
    let timeoutId;
    let running = true;

    return new Promise((resolve, reject) => {
        const runCheck = () => {
            const result = predicate();
            if (result) {
                resolve(result);
            } else if (running) {
                handle = requestAnimationFrame(runCheck);
            } else {
                let message =
                    options?.message || `'waitUntil' timed out after %timeout% milliseconds`;
                if (typeof message === "function") {
                    message = message();
                }
                reject(new HootDomError(message.replace("%timeout%", String(timeout))));
            }
        };

        handle = requestAnimationFrame(runCheck);
        timeoutId = setTimeout(() => (running = false), timeout);
    }).finally(() => {
        cancelAnimationFrame(handle);
        clearTimeout(timeoutId);
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

        super((resolve, reject) => {
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
