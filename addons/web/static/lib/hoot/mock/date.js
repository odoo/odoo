/** @odoo-module */

import { getTimeOffset, isTimeFrozen, resetTimeOffset } from "@web/../lib/hoot-dom/helpers/time";
import { createMock, HootError, isNil } from "../hoot_utils";

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

const { Date, Intl } = globalThis;
const { now: $now, UTC: $UTC } = Date;
const { DateTimeFormat, Locale } = Intl;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * @param {Date} baseDate
 */
function computeTimeZoneOffset(baseDate) {
    const utcDate = new Date(baseDate.toLocaleString(DEFAULT_LOCALE, { timeZone: "UTC" }));
    const tzDate = new Date(baseDate.toLocaleString(DEFAULT_LOCALE, { timeZone: timeZoneName }));
    return (utcDate - tzDate) / 60000; // in minutes
}

/**
 * @param {number} id
 */
function getDateParams() {
    return [...dateParams.slice(0, -1), dateParams.at(-1) + getTimeStampDiff() + getTimeOffset()];
}

function getTimeStampDiff() {
    return isTimeFrozen() ? 0 : $now() - dateTimeStamp;
}

/**
 * @param {string | DateSpecs} dateSpecs
 */
function parseDateParams(dateSpecs) {
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
}

/**
 * @param {typeof dateParams} newDateParams
 */
function setDateParams(newDateParams) {
    dateParams = newDateParams;
    dateTimeStamp = $now();

    resetTimeOffset();
}

/**
 * @param {string | number | null | undefined} tz
 */
function setTimeZone(tz) {
    if (typeof tz === "string") {
        if (!tz.includes("/")) {
            throw new HootError(`invalid time zone: must be in the format <Country/...Location>`);
        }

        // Set TZ name
        timeZoneName = tz;
        // Set TZ offset based on name (must be computed for each date)
        timeZoneOffset = computeTimeZoneOffset;
    } else if (typeof tz === "number") {
        // Only set TZ offset
        timeZoneOffset = tz * -60;
    } else {
        // Reset both TZ name & offset
        timeZoneName = null;
        timeZoneOffset = null;
    }

    for (const callback of timeZoneChangeCallbacks) {
        callback(tz ?? DEFAULT_TIMEZONE_NAME);
    }
}

class MockDateTimeFormat extends DateTimeFormat {
    constructor(locales, options) {
        super(locales, {
            ...options,
            timeZone: options?.timeZone ?? timeZoneName ?? DEFAULT_TIMEZONE_NAME,
        });
    }

    resolvedOptions() {
        return {
            ...super.resolvedOptions(),
            timeZone: timeZoneName ?? DEFAULT_TIMEZONE_NAME,
            locale: locale ?? DEFAULT_LOCALE,
        };
    }
}

const DATE_REGEX =
    /(?<year>\d{4})[/-](?<month>\d{2})[/-](?<day>\d{2})([\sT]+(?<hour>\d{2}):(?<minute>\d{2}):(?<second>\d{2})(\.(?<millisecond>\d{3}))?)?/;
const DEFAULT_DATE = [2019, 2, 11, 9, 30, 0, 0];
const DEFAULT_LOCALE = "en-US";
const DEFAULT_TIMEZONE_NAME = "Europe/Brussels";
const DEFAULT_TIMEZONE_OFFSET = -60;

/** @type {((tz: string | number) => any)[]} */
const timeZoneChangeCallbacks = [];

let dateParams = DEFAULT_DATE;
let dateTimeStamp = $now();
/** @type {string | null} */
let locale = null;
/** @type {string | null} */
let timeZoneName = null;
/** @type {number | ((date: Date) => number) | null} */
let timeZoneOffset = null;

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

export function cleanupDate() {
    setDateParams(DEFAULT_DATE);
    locale = null;
    timeZoneName = null;
    timeZoneOffset = null;
}

/**
 * Mocks the current date and time, and also the time zone if any.
 *
 * Date can either be an object describing the date and time to mock, or a
 * string in SQL or ISO format (time and millisecond values can be omitted).
 * @see {@link mockTimeZone} for the time zone params.
 *
 * @param {string | DateSpecs} [date]
 * @param  {string | number | null} [tz]
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
        setTimeZone(tz);
    }
}

/**
 * Mocks the current locale.
 *
 * If the time zone hasn't been mocked already, it will be assigned to the first
 * time zone available in the given locale (if any).
 *
 * @param {string} newLocale
 * @example
 *  mockTimeZone("ja-JP"); // UTC + 9
 */
export function mockLocale(newLocale) {
    locale = newLocale;

    if (!isNil(locale) && isNil(timeZoneName)) {
        // Set TZ from locale (if not mocked already)
        const firstAvailableTZ = new Locale(locale).timeZones?.[0];
        if (!isNil(firstAvailableTZ)) {
            setTimeZone(firstAvailableTZ);
        }
    }
}

/**
 * Mocks the current time zone.
 *
 * Time zone can either be a time zone or an offset. Number offsets are expressed
 * in hours.
 *
 * @param {string | number | null} [tz]
 * @example
 *  mockTimeZone(+10); // UTC + 10
 * @example
 *  mockTimeZone("Europe/Brussels"); // UTC + 1 (or UTC + 2 in summer)
 * @example
 *  mockTimeZone(null) // Resets to test default (+1)
 */
export function mockTimeZone(tz) {
    setTimeZone(tz);
}

/**
 * Subscribe to changes made on the time zone (mocked) value.
 *
 * @param {(tz: string | number) => any} callback
 */
export function onTimeZoneChange(callback) {
    timeZoneChangeCallbacks.push(callback);
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
        const offset = timeZoneOffset ?? DEFAULT_TIMEZONE_OFFSET;
        return typeof offset === "function" ? offset(this) : offset;
    }

    static now() {
        return new MockDate().getTime();
    }
}

export const MockIntl = createMock(Intl, {
    DateTimeFormat: { value: MockDateTimeFormat },
});
