/** @odoo-module */
/* eslint-disable no-restricted-syntax */

import { isNil } from "../hoot_utils";

/**
 * @typedef DateSpecs
 * @property {number} [year]
 * @property {number} [month] // 1-12
 * @property {number} [day] // 1-31
 * @property {number} [hour] // 0-23
 * @property {number} [minute] // 0-59
 * @property {number} [second] // 0-59
 * @property {number} [millisecond] // 0-999
 */

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const {
    cancelAnimationFrame,
    clearInterval,
    clearTimeout,
    Date,
    Error,
    Math: { ceil: $ceil, max: $max },
    performance,
    Promise,
    requestAnimationFrame,
    setInterval,
    setTimeout,
} = globalThis;
const { now: $now, UTC: $UTC } = Date;
/** @type {Performance["now"]} */
const $performanceNow = performance.now.bind(performance);

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * @param {Iterable<[string, [() => any, number, number]]>} values
 */
const addToTimerStack = (values) => {
    if (!targetTime) {
        return;
    }
    for (const [internalId, [callback, init, delay]] of values) {
        const timeout = init + delay;
        if (timeout <= targetTime) {
            timerStack.push([callback, timeout, internalId]);
        }
    }
    timerStack.sort((a, b) => a[1] - b[1]);
};

/**
 * @param {number} id
 */
const animationToId = (id) => ID_PREFIX.animation + String(id);

const getDateParams = () => [
    ...dateParams.slice(0, -1),
    dateParams.at(-1) + ($now() - dateTimeStamp) + timeOffset,
];

/**
 * @param {string} timeZone
 * @param {Date} baseDate
 */
const getOffsetFromTimeZone = (timeZone, baseDate) => {
    if (!timeZone.includes("/")) {
        // Time zone is a locale
        // ! Warning: does not work in Firefox
        timeZone = new Intl.Locale(timeZone).timeZones?.[0] ?? null;
    }
    const utcDate = new Date(baseDate.toLocaleString("en-US", { timeZone: "UTC" }));
    const tzDate = new Date(baseDate.toLocaleString("en-US", { timeZone }));
    return (utcDate.getTime() - tzDate.getTime()) / 60_000; // in minutes
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

const now = () => $performanceNow() + timeOffset;

/**
 * @param {string | DateSpecs} dateSpecs
 */
const parseDateParams = (dateSpecs) => {
    /** @type {DateSpecs} */
    const specs =
        (typeof dateSpecs === "string" ? dateSpecs.match(DATE_REGEX)?.groups : dateSpecs) || {};
    return [
        specs.year ?? DEFAULT_DATE[0],
        (specs.month ?? DEFAULT_DATE[1]) - 1,
        specs.day ?? DEFAULT_DATE[2],
        specs.hour ?? DEFAULT_DATE[3],
        specs.minute ?? DEFAULT_DATE[4],
        specs.second ?? DEFAULT_DATE[5],
        specs.millisecond ?? DEFAULT_DATE[6],
    ].map(Number);
};

/**
 * @param {typeof dateParams} newDateParams
 */
const setDateParams = (newDateParams) => {
    dateParams = newDateParams;
    dateTimeStamp = $now();
    timeOffset = 0;
};

/**
 * @param {number} id
 */
const timeoutToId = (id) => ID_PREFIX.timeout + String(id);

const ID_PREFIX = {
    animation: "a_",
    interval: "i_",
    timeout: "t_",
};
const DATE_REGEX =
    /(?<year>\d{4})[/-](?<month>\d{2})[/-](?<day>\d{2})([\sT]+(?<hour>\d{2}):(?<minute>\d{2}):(?<second>\d{2})(\.(?<millisecond>\d{3}))?)?/;
const DEFAULT_DATE = [2019, 2, 11, 9, 30, 0, 0];
const DEFAULT_TIMEZONE = +1;

/** @type {Map<string, [() => any, number, number]>} */
const timers = new Map();
/** @type {[() => any, number, string][]} */
const timerStack = [];

let allowTimers = true;
let dateParams = DEFAULT_DATE;
let dateTimeStamp = $now();
let frameDelay = 1000 / 60;
let targetTime = 0;
/** @type {string | number} */
let timeZone = DEFAULT_TIMEZONE;
let timeOffset = 0;

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * @param {number} [frameCount]
 */
export async function advanceFrame(frameCount) {
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
export async function advanceTime(ms) {
    const baseTime = now();
    let remainingMs = ms;
    targetTime = baseTime + ms;

    addToTimerStack(timers.entries());

    while (timerStack.length) {
        const [handler, timeout, id] = timerStack.shift();
        const diff = $max(timeout - baseTime, 0);
        remainingMs -= diff;
        timeOffset += diff;
        if (timers.has(id)) {
            handler(timeout);
        }
    }

    targetTime = 0;
    if (remainingMs > 0) {
        timeOffset += remainingMs;
    }

    // Waits for callbacks to execute
    await animationFrame();

    return ms;
}

/**
 * Returns a promise resolved after the next animation frame, typically allowing
 * Owl components to render.
 *
 * @returns {Promise<void>}
 */
export async function animationFrame() {
    await new Promise((resolve) => requestAnimationFrame(resolve));
    await delay();
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
    await runAllTimers(true);

    setDateParams(DEFAULT_DATE);
    timeZone = DEFAULT_TIMEZONE;
}

/**
 * Returns a promise resolved after a given amount of milliseconds (default to 0).
 *
 * @param {number} [duration]
 * @returns {Promise<void>}
 * @example
 *  await delay(1000); // waits for 1 second
 */
export async function delay(duration) {
    await new Promise((resolve) => setTimeout(resolve, duration));
}

/**
 * Returns a promise resolved after the next microtask tick.
 *
 * @returns {Promise<void>}
 */
export async function microTick() {
    await Promise.resolve();
}

/**
 * Mocks the current date and time, and also the time zone if any.
 *
 * Date can either be an object describing the date and time to mock, or a
 * string in SQL or ISO format (time and millisecond values can be omitted).
 * @see {@link mockTimeZone} for the time zone params.
 *
 * @param {string | DateSpecs} [date]
 * @param  {string | number} [tz]
 * @example
 *  mockDate("2023-12-25T20:45:00"); // 2023-12-25 20:45:00 UTC
 * @example
 *  mockDate({ year: 2023, month: 12, day: 25, hour: 20, minute: 45 }); // same as above
 * @example
 *  mockDate("2019-02-11 09:30:00.001", +2);
 */
export function mockDate(date, tz) {
    setDateParams(date ? parseDateParams(date) : DEFAULT_DATE);
    if (!isNil(tz)) {
        mockTimeZone(tz);
    }
}

/** @type {typeof cancelAnimationFrame} */
export function mockedCancelAnimationFrame(handle) {
    cancelAnimationFrame(handle);
    timers.delete(animationToId(handle));
}

/** @type {typeof clearInterval} */
export function mockedClearInterval(intervalId) {
    clearInterval(intervalId);
    timers.delete(intervalToId(intervalId));
}

/** @type {typeof clearTimeout} */
export function mockedClearTimeout(timeoutId) {
    clearTimeout(timeoutId);
    timers.delete(timeoutToId(timeoutId));
}

/** @type {typeof requestAnimationFrame} */
export function mockedRequestAnimationFrame(callback) {
    if (!allowTimers) {
        return 0;
    }

    /**
     * @param {number} delta
     */
    const handler = (delta) => {
        mockedCancelAnimationFrame(handle);
        return callback(delta ?? now() - animationValues[1]);
    };

    const animationValues = [handler, now(), frameDelay];
    const handle = requestAnimationFrame(handler);
    const internalId = animationToId(handle);
    timers.set(internalId, animationValues);

    addToTimerStack([[internalId, animationValues]]);

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
            intervalValues[1] += ms;
        } else {
            mockedClearInterval(intervalId);
        }
        return callback(...args);
    };

    const intervalValues = [handler, now(), ms];
    const intervalId = setInterval(handler, ms);
    const internalId = intervalToId(intervalId);
    timers.set(internalId, intervalValues);

    addToTimerStack([[internalId, intervalValues]]);

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
    const timeoutId = setTimeout(handler, ms);
    const internalId = timeoutToId(timeoutId);
    timers.set(internalId, timeoutValues);

    addToTimerStack([[internalId, timeoutValues]]);

    return timeoutId;
}

/**
 * Mocks the current time zone.
 *
 * Time zone can either be a locale, a time zone or an offset.
 *
 * Returns a function restoring the default zone.
 *
 * @param {string | number} [tz]
 * @example
 *  mockTimeZone(+1); // UTC + 1
 * @example
 *  mockTimeZone("Europe/Brussels"); // UTC + 1 (or UTC + 2 in summer)
 * @example
 *  mockTimeZone("ja-JP"); // UTC + 9
 */
export function mockTimeZone(tz) {
    timeZone = tz ?? DEFAULT_TIMEZONE;
}

/**
 * Calculates the amount of time needed to run all current timeouts, intervals and
 * animations, and then advances the current time by that amount.
 *
 * @see {@link advanceTime}
 * @param {boolean} [preventTimers=false]
 * @returns {Promise<number>} time consumed by timers (in ms).
 */
export async function runAllTimers(preventTimers = false) {
    if (!timers.size) {
        return 0;
    }

    if (preventTimers) {
        allowTimers = false;
    }

    const endts = $max(...[...timers.values()].map(([, init, delay]) => init + delay));
    const ms = await advanceTime($ceil(endts - now()));

    if (preventTimers) {
        allowTimers = true;
    }

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

/**
 * Returns a promise resolved after the next task tick.
 *
 * @returns {Promise<void>}
 */
export async function tick() {
    await delay();
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
    #resolve;
    /** @type {typeof Promise.reject<T>} */
    #reject;

    /**
     * @param {(resolve: (value: T) => void, reject: (reason?: any) => void) => void} [executor]
     */
    constructor(executor) {
        let _resolve, _reject;

        super((resolve, reject) => {
            _resolve = resolve;
            _reject = reject;
            return executor?.(resolve, reject);
        });

        this.#resolve = _resolve;
        this.#reject = _reject;
    }

    /**
     * @param {any} [reason]
     */
    reject(reason) {
        return this.#reject(reason);
    }

    /**
     * @param {T} [value]
     */
    resolve(value) {
        return this.#resolve(value);
    }
}

export class MockDate extends Date {
    constructor(...args) {
        if (args.length === 1) {
            super(args[0]);
        } else {
            const params = getDateParams();
            for (let i = 0; i < params.length; i++) {
                args[i] ??= params[i];
            }
            super($UTC(...args));
        }
    }

    getTimezoneOffset() {
        if (typeof timeZone === "string") {
            // Time zone is a locale or a time zone
            return getOffsetFromTimeZone(timeZone, this);
        } else {
            // Time zone is an offset
            return -(timeZone * 60);
        }
    }

    static now() {
        return new MockDate().getTime() + ($now() - dateTimeStamp) + timeOffset;
    }
}
