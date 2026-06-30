/** @odoo-module **/

import { localization } from "@web/core/l10n/localization";
import { _t } from "@web/core/l10n/translation";
import { memoize } from "@web/core/utils/functions";
import { ensureArray } from "../utils/arrays";

const { DateTime, Settings } = luxon;

/**
 * @typedef ConversionOptions
 *  This is a list of the available options to either:
 *  - convert a DateTime to a string (format)
 *  - convert a string to a DateTime (parse)
 *  All of these are optional and the default values are issued by the Localization service.
 *
 * @property {string} [format]
 *  Format used to format a DateTime or to parse a formatted string.
 *  > Default: the session localization format.
 *
 * @typedef {luxon.DateTime} DateTime
 *
 * @typedef {[NullableDateTime, NullableDateTime]} NullableDateRange
 *
 * @typedef {DateTime | false | null | undefined} NullableDateTime
 */

/**
 * Limits defining a valid date.
 * This is needed because the server only understands 4-digit years.
 * Note: both of these are in the local timezone
 */
export const MIN_VALID_DATE = DateTime.fromObject({ year: 1000 });
export const MAX_VALID_DATE = DateTime.fromObject({ year: 9999 }).endOf("year");

const SERVER_DATE_FORMAT = "yyyy-MM-dd";
const SERVER_TIME_FORMAT = "HH:mm:ss";
const SERVER_DATETIME_FORMAT = `${SERVER_DATE_FORMAT} ${SERVER_TIME_FORMAT}`;

const nonAlphaRegex = /[^a-z]/gi;
const nonDigitRegex = /[^\d]/g;

const normalizeFormatTable = {
    // Python strftime to luxon.js conversion table
    // See odoo/addons/base/views/res_lang_views.xml
    // for details about supported directives
    a: "ccc",
    A: "cccc",
    b: "MMM",
    B: "MMMM",
    d: "dd",
    H: "HH",
    I: "hh",
    j: "o",
    m: "MM",
    M: "mm",
    p: "a",
    S: "ss",
    W: "WW",
    w: "c",
    y: "yy",
    Y: "yyyy",
    c: "ccc MMM d HH:mm:ss yyyy",
    x: "MM/dd/yy",
    X: "HH:mm:ss",
};

const smartDateUnits = {
    d: "days",
    m: "months",
    w: "weeks",
    y: "years",
};
const smartDateRegex = new RegExp(
    ["^", "([+-])", "(\\d+)", `([${Object.keys(smartDateUnits).join("")}]?)`, "$"].join("\\s*"),
    "i"
);

/** @type {WeakMap<DateTime, string>} */
const dateCache = new WeakMap();
/** @type {WeakMap<DateTime, string>} */
const dateTimeCache = new WeakMap();

export class ConversionError extends Error {
    name = "ConversionError";
}

//-----------------------------------------------------------------------------
// Helpers
//-----------------------------------------------------------------------------

/**
 * Checks whether 2 given dates or date ranges are equal. Both values are allowed
 * to be falsy or to not be of the same type (which will return false).
 *
 * @param {NullableDateTime | NullableDateRange} d1
 * @param {NullableDateTime | NullableDateRange} d2
 * @returns {boolean}
 */
export function areDatesEqual(d1, d2) {
    if (Array.isArray(d1) || Array.isArray(d2)) {
        // One of the values is a date range -> checks deep equality between the ranges
        d1 = ensureArray(d1);
        d2 = ensureArray(d2);
        return d1.length === d2.length && d1.every((d1Val, i) => areDatesEqual(d1Val, d2[i]));
    }
    if (d1 instanceof DateTime && d2 instanceof DateTime && d1 !== d2) {
        // Both values are DateTime objects -> use Luxon's comparison
        return d1.equals(d2);
    } else {
        // One of the values is not a DateTime object -> fallback to strict equal
        return d1 === d2;
    }
}

/**
 * @param {DateTime} desired
 * @param {DateTime} minDate
 * @param {DateTime} maxDate
 */
export function clampDate(desired, minDate, maxDate) {
    if (maxDate < desired) {
        return maxDate;
    }
    if (minDate > desired) {
        return minDate;
    }
    return desired;
}

/**
 * Returns whether the given format is a 24-hour format.
 * Falls back to localization time format if none is given.
 *
 * @param {string} format
 */
export function is24HourFormat(format) {
    return /H/.test(format || localization.timeFormat);
}

/**
 * @param {NullableDateTime | NullableDateRange} value
 * @param {NullableDateRange} range
 * @returns {boolean}
 */
export function isInRange(value, range) {
    if (!value || !range) {
        return false;
    }
    if (Array.isArray(value)) {
        const actualValues = value.filter(Boolean);
        if (actualValues.length < 2) {
            return isInRange(actualValues[0], range);
        }
        return (
            (value[0] <= range[0] && range[0] <= value[1]) ||
            (range[0] <= value[0] && value[0] <= range[1])
        );
    } else {
        return range[0] <= value && value <= range[1];
    }
}

/**
 * Returns whether the given format uses a meridiem suffix (AM/PM).
 * Falls back to localization time format if none is given.
 *
 * @param {string} format
 */
export function isMeridiemFormat(format) {
    return /a/.test(format || localization.timeFormat);
}

/**
 * Returns whether the given DateTime is valid.
 * The date is considered valid if it:
 * - is a DateTime object
 * - has the "isValid" flag set to true
 * - is between 1000-01-01 and 9999-12-31 (both included)
 * @see MIN_VALID_DATE
 * @see MAX_VALID_DATE
 *
 * @param {NullableDateTime} date
 */
function isValidDate(date) {
    return date && date.isValid && isInRange(date, [MIN_VALID_DATE, MAX_VALID_DATE]);
}

/**
 * Smart date inputs are shortcuts to write dates quicker.
 * These shortcuts should respect the format ^[+-]\d+[dmwy]?$
 *
 * e.g.
 *   "+1d" or "+1" will return now + 1 day
 *   "-2w" will return now - 2 weeks
 *   "+3m" will return now + 3 months
 *   "-4y" will return now + 4 years
 *
 * @param {string} value
 * @returns {NullableDateTime} Luxon datetime object (in the user's local timezone)
 */
function parseSmartDateInput(value) {
    const match = value.match(smartDateRegex);
    if (match) {
        let date = DateTime.local();
        const offset = parseInt(match[2], 10);
        const unit = smartDateUnits[(match[3] || "d").toLowerCase()];
        if (match[1] === "+") {
            date = date.plus({ [unit]: offset });
        } else {
            date = date.minus({ [unit]: offset });
        }
        return date;
    }
    return false;
}

/**
 * Removes any duplicate *subsequent* alphabetic characters in a given string.
 * Example: "aa-bb-CCcc-ddD-c xxxx-Yy-ZZ" -> "a-b-Cc-dD-c x-Yy-Z"
 *
 * @type {(str: string) => string}
 */
const stripAlphaDupes = memoize(function stripAlphaDupes(str) {
    return str.replace(/[a-z]/gi, (letter, index, str) =>
        letter === str[index - 1] ? "" : letter
    );
});

/**
 * Convert Python strftime to escaped luxon.js format.
 *
 * @type {(format: string) => string}
 */
export const strftimeToLuxonFormat = memoize(function strftimeToLuxonFormat(format) {
    const output = [];
    let inToken = false;
    for (let index = 0; index < format.length; ++index) {
        let character = format[index];
        if (character === "%" && !inToken) {
            inToken = true;
            continue;
        }
        if (/[a-z]/gi.test(character)) {
            if (inToken && normalizeFormatTable[character] !== undefined) {
                character = normalizeFormatTable[character];
            } else {
                character = `'${character}'`; // luxon escape
            }
        }
        output.push(character);
        inToken = false;
    }
    return output.join("");
});

/**
 * Lazy getter returning the start of the current day.
 */
export function today() {
    return DateTime.local().startOf("day");
}

//-----------------------------------------------------------------------------
// Formatting
//-----------------------------------------------------------------------------

/**
 * Formats a DateTime object to a date string
 *
 * @param {NullableDateTime} value
 * @param {ConversionOptions} [options={}]
 */
export function formatDate(value, options = {}) {
    if (!value) {
        return "";
    }
    const format = options.format || localization.dateFormat;
    return value.toFormat(format);
}

/**
 * Formats a DateTime object to a datetime string
 *
 * @param {NullableDateTime} value
 * @param {ConversionOptions} [options={}]
 */
export function formatDateTime(value, options = {}) {
    if (!value) {
        return "";
    }
    const format = options.format || localization.dateTimeFormat;
    return value.setZone("default").toFormat(format);
}

/**
 * Converts a given duration in seconds into a human-readable format.
 *
 * The function takes a duration in seconds and converts it into a human-readable form,
 * such as "1h" or "1 hour, 30 minutes", depending on the value of the `showFullDuration` parameter.
 * If the `showFullDuration` is set to true, the function will display up to two non-zero duration
 * components in long form (e.g: hours, minutes).
 * Otherwise, it will show just the largest non-zero duration component in narrow form (e.g: y or h).
 * Luxon takes care of translations given the current locale.
 *
 * @param {number} seconds - The duration in seconds to be converted.
 * @param {boolean} showFullDuration - If true, the output will have two components in long form.
 * Otherwise, just one component will be displayed in narrow form.
 *
 * @returns {string} A human-readable string representation of the duration.
 *
 * @example
 * // Sample usage
 * const durationInSeconds = 7320; // 2 hours and 2 minutes (2 * 3600 + 2 * 60)
 * const fullDuration = humanizeDuration(durationInSeconds, true);
 * console.log(fullDuration); // Output: "2 hours, 2 minutes"
 *
 * const shortDuration = humanizeDuration(durationInSeconds, false);
 * console.log(shortDuration); // Output: "2h"
 */
export function formatDuration(seconds, showFullDuration) {
    const displayStyle = showFullDuration ? "long" : "narrow";
    const numberOfValuesToDisplay = showFullDuration ? 2 : 1;
    const durationKeys = ["years", "months", "days", "hours", "minutes"];

    if (seconds < 60) {
        seconds = 60;
    }
    seconds -= seconds % 60;

    let duration = luxon.Duration.fromObject({ seconds: seconds }).shiftTo(...durationKeys);
    duration = duration.shiftTo(...durationKeys.filter((key) => duration.get(key)));
    const durationSplit = duration.toHuman({ unitDisplay: displayStyle }).split(",");

    if (!showFullDuration && duration.loc.locale.includes("en") && duration.months > 0) {
        durationSplit[0] = durationSplit[0].replace("m", "M");
    }
    return durationSplit.slice(0, numberOfValuesToDisplay).join(",");
}

/**
 * Formats the given DateTime to the server date format.
 * @param {DateTime} value
 * @returns {string}
 */
export function serializeDate(value) {
    if (!dateCache.has(value)) {
        dateCache.set(value, value.toFormat(SERVER_DATE_FORMAT, { numberingSystem: "latn" }));
    }
    return dateCache.get(value);
}

/**
 * Formats the given DateTime to the server datetime format.
 * @param {DateTime} value
 * @returns {string}
 */
export function serializeDateTime(value) {
    if (!dateTimeCache.has(value)) {
        dateTimeCache.set(
            value,
            value.setZone("utc").toFormat(SERVER_DATETIME_FORMAT, { numberingSystem: "latn" })
        );
    }
    return dateTimeCache.get(value);
}

//-----------------------------------------------------------------------------
// Parsing
//-----------------------------------------------------------------------------

/**
 * Parses a string value to a Luxon DateTime object.
 *
 * @param {string} value
 * @param {ConversionOptions} [options={}]
 *
 * @see parseDateTime (Note: since we're only interested by the date itself, the
 *  returned value will always be set at the start of the day)
 */
export function parseDate(value, options = {}) {
    const parsed = parseDateTime(value, { ...options, format: options.format || localization.dateFormat });
    return parsed && parsed.startOf("day");
}

/**
 * Parses a string value to a Luxon DateTime object.
 *
 * @param {string} value value to parse.
 *  - Value can take the form of a smart date:
 *    e.g. "+3w" for three weeks from now.
 *    (`options.format` is ignored in this case)
 *
 *  - If value cannot be parsed within the provided format,
 *    ISO8601 and SQL formats are then tried. If these formats
 *    include a timezone information, the returned value will
 *    still be set to the user's timezone.
 *    e.g. "2020-01-01T12:00:00+06:00" with the user's timezone being UTC+1,
 *         the returned value will express the same timestamp but in UTC+1 (here time will be 7:00).
 *
 * @param {ConversionOptions} options
 *
 * @returns {NullableDateTime} Luxon DateTime object in user's timezone
 */
export function parseDateTime(value, options = {}) {
    if (!value) {
        return false;
    }

    const fmt = options.format || localization.dateTimeFormat;
    const parseOpts = {
        setZone: true,
        zone: "default",
    };
    const switchToLatin = Settings.defaultNumberingSystem !== "latn" && /[0-9]/.test(value);

    // Force numbering system to latin if actual numbers are found in the value
    if (switchToLatin) {
        parseOpts.numberingSystem = "latn";
    }

    // Base case: try parsing with the given format and options
    let result = DateTime.fromFormat(value, fmt, parseOpts);

    // Try parsing as a smart date
    if (!isValidDate(result)) {
        result = parseSmartDateInput(value);
    }

    // Try parsing with partial date parts
    if (!isValidDate(result)) {
        const fmtWoZero = stripAlphaDupes(fmt);
        result = DateTime.fromFormat(value, fmtWoZero, parseOpts);
    }

    // Try parsing with custom shorthand date parts
    if (!isValidDate(result)) {
        // Luxon is not permissive regarding delimiting characters in the format.
        // So if the value to parse has less characters than the format, we would
        // try to parse without the delimiting characters.
        const digitList = value.split(nonDigitRegex).filter(Boolean);
        const fmtList = fmt.split(nonAlphaRegex).filter(Boolean);
        const valWoSeps = digitList.join("");

        // This is the weird part: we try to adapt the given format to comply with
        // the amount of digits in the given value. To do this we split the format
        // and the value on non-letter and non-digit characters respectively. This
        // should create the same amount of grouping parameters, and the format
        // groups are trimmed according to the length of their corresponding
        // digit group. The 'carry' variable allows for the length of a digit
        // group to overflow to the next format group. This is typically the case
        // when the given value doesn't have non-digit separators and generates
        // one big digit group instead.
        let carry = 0;
        const fmtWoSeps = fmtList
            .map((part, i) => {
                const digitLength = (digitList[i] || "").length;
                const actualPart = part.slice(0, digitLength + carry);
                carry += digitLength - actualPart.length;
                return actualPart;
            })
            .join("");

        result = DateTime.fromFormat(valWoSeps, fmtWoSeps, parseOpts);
    }

    // Try with defaul ISO or SQL formats
    if (!isValidDate(result)) {
        // Also try some fallback formats, but only if value counts more than
        // four digit characters as this could get misinterpreted as the time of
        // the actual date.
        const valueDigits = value.replace(nonDigitRegex, "");
        if (valueDigits.length > 4) {
            result = DateTime.fromISO(value, parseOpts); // ISO8601
            if (!isValidDate(result)) {
                result = DateTime.fromSQL(value, parseOpts); // last try: SQL
            }
        }
    }

    // No working parsing methods: throw an error
    if (!isValidDate(result)) {
        throw new ConversionError(_t("'%s' is not a correct date or datetime", value));
    }

    // Revert to original numbering system
    if (switchToLatin) {
        result = result.reconfigure({
            numberingSystem: Settings.defaultNumberingSystem,
        });
    }

    return result.setZone("default");
}

/**
 * Returns a date object parsed from the given serialized string.
 * @param {string} value serialized date string, e.g. "2018-01-01"
 */
export function deserializeDate(value, options = {}) {
    const defaultDict = {numberingSystem: "latn", zone: "default"}
    const joinedDict = {...defaultDict, ...options}
    return DateTime.fromSQL(value, joinedDict).reconfigure({
        numberingSystem: Settings.defaultNumberingSystem,
    });
}

/**
 * Returns a datetime object parsed from the given serialized string.
 * @param {string} value serialized datetime string, e.g. "2018-01-01 00:00:00", expressed in UTC
 */
export function deserializeDateTime(value) {
    return DateTime.fromSQL(value, { numberingSystem: "latn", zone: "utc" })
        .setZone("default")
        .reconfigure({
            numberingSystem: Settings.defaultNumberingSystem,
        });
}
