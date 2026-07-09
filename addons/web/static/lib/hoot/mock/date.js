/** @odoo-module */

import { getTimeOffset, isTimeFrozen, resetTimeOffset } from "@web/../lib/hoot-dom/helpers/time";
import { createMock, HootError, isNil } from "../hoot_utils";
import { ensureTest } from "../main_runner";

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
const { now: $now } = Date;
const { DateTimeFormat, Locale } = Intl;
const { abs: $abs, floor: $floor } = Math;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * Returns a list of offsets to add to each date parameter.
 *
 * These offsets are arranged in the same order as the Date constructor parameters;
 * starting with the 'years' and ending with the 'milliseconds'.
 *
 * Note that the offset could simply be added to the 'milliseconds' part, and JavaScript
 * would handle the diff itself, but the thing is we want to ignore this offset
 * for arguments that are given explicitly.
 *
 * For example:
 *  `new Date(2022, 0, 1)` -> we want the offset applied on the 'hours' part as
 *      it was omitted, and thus will be filled with the corresponding {@link dateParams}
 *      bit;
 *  `new Date(2022, 0, 1, 8)` -> here the offset needs to be applied up until the
 *      'minutes' part, as the hour is now fixed by a given parameter.
 *
 * @param {number[]} args
 */
function computeOffsetParams(args) {
    if (args.length === 1 || args.length >= 7) {
        // 1 argument = unique ms timestamp
        // 7 arguments = no need to autofill/offset parameters
        return args;
    }

    // Auto-fill remaining arguments with mock date parameters
    for (let i = args.length; i < dateParams.length; i++) {
        args[i] = dateParams[i];
    }

    // Warning: the actual offset needs to be acquired dynamically, as it may depend
    // on the date (i.e. daylight savings). Note that it is also computed with auto-filled
    // 'dateParams' as these could shift the date as well.
    const realOffset = new Date(...args).getTimezoneOffset() * -60_000;

    // The offset value is the sum of:
    //  - the elapsed time from the beginning of the test;
    //  - the artifical offset, affected by helpers such as 'advanceTime';
    //  - the real TZ offset, as the 'dateParams' object holds UTC values.
    let offset = getTimeStampDiff() + getTimeOffset() + realOffset;

    // Add the offset to each part:
    //  - starting from the 'milliseconds' part (index 6)
    //  - stopping when there is no more offset to add
    //  - for each part: add the offset and carry the overflow to the next
    for (let i = 6; i >= 0 && offset > 0; i--) {
        const maxValue = OFFSET_MAX_VALUES[$abs(i - 6)];
        if (!maxValue) {
            // Offset is beyoud the 'hours' part: no need to add it for each part
            args[i] += offset;
            break;
        }
        // Combine the current value to the offset
        offset += args[i];
        // Set the current value to the maximum available value
        args[i] = offset % maxValue;
        // Carry the remainder to the next part
        offset = $floor(offset / maxValue);
    }

    return args;
}

/**
 * Returns the timezone offset from a given date, in minutes.
 *
 * @param {Date} baseDate
 */
function computeTimeZoneOffset(baseDate) {
    const utcDate = new Date(baseDate.toLocaleString(DEFAULT_LOCALE, { timeZone: "UTC" }));
    const tzDate = new Date(baseDate.toLocaleString(DEFAULT_LOCALE, { timeZone: timeZoneName }));
    return (utcDate - tzDate) / 60_000;
}

/**
 * Returns the elapsed time from the beginning of a test (in milliseconds), or 0
 * if time has been frozen (see {@link isTimeFrozen} for more info).
 */
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

    /** @type {Intl.DateTimeFormat["format"]} */
    format(date) {
        return super.format(date || new MockDate());
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

const OFFSET_MAX_VALUES = [
    1000, // milliseconds
    60, // seconds
    60, // minutes
    24, // hours
];

/** @type {((tz: string | number) => any)[]} */
const timeZoneChangeCallbacks = [];

/**
 * Current UTC mocked date parameters; these are arranged in the same way as the
 * arguments of the `Date` constructor: Y,M,D,h,m,s,ms
 */
let dateParams = DEFAULT_DATE;
/**
 * Start time registered at the beginning of a test.
 * This is needed by {@link getTimeStampDiff} to get the current elapsed time (in
 * milliseconds), or `0` if time has been frozen.
 */
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
 * @param {string | number | null} [tz]
 * @example
 *  mockDate("2023-12-25T20:45:00"); // 2023-12-25 20:45:00 UTC
 * @example
 *  mockDate({ year: 2023, month: 12, day: 25, hour: 20, minute: 45 }); // same as above
 * @example
 *  mockDate("2019-02-11 09:30:00.001", +2);
 */
export function mockDate(date, tz) {
    ensureTest("mockDate");
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
    ensureTest("mockLocale");
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
    ensureTest("mockTimeZone");
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

/**
 * Mocked version of the {@link Date} constructor, automatically adding any offset
 * from elapsed time or added by test helpers.
 *
 * @see {@link computeOffsetParams} for more details about the offset processing.
 */
export class MockDate extends Date {
    constructor(...args) {
        super(...computeOffsetParams(args));
    }

    getTimezoneOffset() {
        return typeof timeZoneOffset === "function"
            ? timeZoneOffset(this)
            : (timeZoneOffset ?? DEFAULT_TIMEZONE_OFFSET);
    }

    static now() {
        return new MockDate().getTime();
    }
}

export const MockIntl = createMock(Intl, {
    DateTimeFormat: { value: MockDateTimeFormat },
});
