/** @odoo-module */

import { getTimeOffset, isTimeFreezed, resetTimeOffset } from "@web/../lib/hoot-dom/helpers/time";

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

const { Date } = globalThis;
const { now: $now, UTC: $UTC } = Date;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * @param {number} id
 */
const getDateParams = () => [
    ...dateParams.slice(0, -1),
    dateParams.at(-1) + getTimeStampDiff() + getTimeOffset(),
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

const getTimeStampDiff = () => (isTimeFreezed() ? 0 : $now() - dateTimeStamp);

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

    resetTimeOffset();
};

const DATE_REGEX =
    /(?<year>\d{4})[/-](?<month>\d{2})[/-](?<day>\d{2})([\sT]+(?<hour>\d{2}):(?<minute>\d{2}):(?<second>\d{2})(\.(?<millisecond>\d{3}))?)?/;
const DEFAULT_DATE = [2019, 2, 11, 9, 30, 0, 0];
const DEFAULT_TIMEZONE = +1;

let dateParams = DEFAULT_DATE;
let dateTimeStamp = $now();
/** @type {string | number} */
let timeZone = DEFAULT_TIMEZONE;

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

export function cleanupDate() {
    setDateParams(DEFAULT_DATE);
    timeZone = DEFAULT_TIMEZONE;
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
    if (tz !== null && tz !== undefined) {
        mockTimeZone(tz);
    }
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

    mockTimeZone.onCall?.(tz);
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
        return new MockDate().getTime();
    }
}
