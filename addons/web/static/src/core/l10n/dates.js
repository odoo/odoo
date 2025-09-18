// @ts-check

/** @module @web/core/l10n/dates - Luxon-based date/datetime parsing, formatting, serialization, and locale-aware week helpers */

import { localization } from "@web/core/l10n/localization";
import { _t } from "@web/core/l10n/translation";
import { memoize } from "@web/core/utils/functions";

import { isInRange, today } from "./date_utils";

// Re-export extracted modules for backward compatibility
export {
    deserializeDate,
    deserializeDateTime,
    serializeDate,
    serializeDateTime,
} from "./date_serialization";
export {
    areDatesEqual,
    clampDate,
    getEndOfLocalWeek,
    getLocalYearAndWeek,
    getStartOfLocalWeek,
    isInRange,
    today,
} from "./date_utils";

const { DateTime, Settings } = /** @type {any} */ (luxon);

/**
 * @typedef ConversionOptions
 * @property {string} [format]
 * @property {string} [tz]
 *
 * @typedef {any} DateTime
 * @typedef {[NullableDateTime, NullableDateTime]} NullableDateRange
 * @typedef {any} NullableDateTime
 */

/**
 * @typedef ConversionLocalOptions
 * @property {boolean} [showSeconds]
 * @property {boolean} [showTime]
 * @property {boolean} [showDate]
 * @property {string} [tz]
 */

/**
 * Limits defining a valid date (server only understands 4-digit years).
 */
export const MIN_VALID_DATE = DateTime.fromObject({ year: 1000 });
export const MAX_VALID_DATE = DateTime.fromObject({ year: 9999 }).endOf("year");

const nonAlphaRegex = /[^a-z]/gi;
const nonDigitRegex = /[^\d]/g;

const normalizeFormatTable = {
    // Python strftime to luxon.js conversion table
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
    H: "hours",
    M: "minutes",
    S: "seconds",
};
const smartWeekdays = {
    monday: 1,
    tuesday: 2,
    wednesday: 3,
    thursday: 4,
    friday: 5,
    saturday: 6,
    sunday: 7,
};

export class ConversionError extends Error {
    name = "ConversionError";
}

//-----------------------------------------------------------------------------
// Helpers
//-----------------------------------------------------------------------------

/**
 * Returns whether the given DateTime is valid (between 1000-01-01 and 9999-12-31).
 * @param {NullableDateTime} date
 */
function isValidDate(date) {
    return date && date.isValid && isInRange(date, [MIN_VALID_DATE, MAX_VALID_DATE]);
}

/**
 * Smart date inputs are shortcuts to write dates quicker.
 *
 * @param {string} value
 * @returns {NullableDateTime}
 */
function parseSmartDateInput(value) {
    const terms = value.split(/\s+/);
    if (!terms.length) {
        return false;
    }
    let now = DateTime.local().startOf("second");
    if (terms[0] === "today") {
        terms.shift();
        now = now.startOf("day");
    } else if (terms[0] === "now") {
        terms.shift();
    } else if (terms.length === 1 && /^[=+-]\d+$/.test(terms[0])) {
        terms[0] += "d";
    }

    for (let i = 0; i < terms.length; i++) {
        const term = terms[i];
        const operator = term[0];
        if (term.length < 3 || !["+", "-", "="].includes(operator)) {
            return false;
        }

        const dayname = term.slice(1);
        if (Object.hasOwn(smartWeekdays, dayname) || dayname === "week_start") {
            const { weekStart } = localization;
            const weekdayNumber =
                dayname === "week_start" ? weekStart : smartWeekdays[dayname];
            let weekdayOffset =
                ((weekdayNumber - weekStart + 7) % 7) -
                ((now.weekday - weekStart + 7) % 7);
            if (operator === "+" || operator === "-") {
                if (weekdayOffset > 0 && operator === "-") {
                    weekdayOffset -= 7;
                } else if (weekdayOffset < 0 && operator === "+") {
                    weekdayOffset += 7;
                }
            } else {
                now = now.startOf("day");
            }
            now = now.plus({ days: weekdayOffset });
            continue;
        }

        try {
            const field_name = smartDateUnits[term.at(-1)];
            const number = parseInt(term.slice(1, -1), 10);
            if (!field_name || isNaN(number)) {
                return false;
            }
            if (operator === "+") {
                now = now.plus({ [field_name]: number });
            } else if (operator === "-") {
                now = now.minus({ [field_name]: number });
            } else if (operator === "=") {
                if (
                    field_name === "seconds" ||
                    field_name === "minutes" ||
                    field_name === "hours"
                ) {
                    now = now.startOf(field_name);
                } else if (field_name === "weeks") {
                    return false;
                } else {
                    now = now.startOf("day");
                }
                now = now.set({ [field_name]: number });
            }
        } catch {
            return false;
        }
    }

    return now;
}

/**
 * Removes duplicate subsequent alphabetic characters.
 * @type {(str: string) => string}
 */
const stripAlphaDupes = memoize(function stripAlphaDupes(str) {
    return str.replace(/[a-z]/gi, (letter, index, str) =>
        letter === str[index - 1] ? "" : letter,
    );
});

/**
 * Convert Python strftime to escaped luxon.js format.
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
                character = `'${character}'`;
            }
        }
        output.push(character);
        inToken = false;
    }
    return output.join("");
});

//-----------------------------------------------------------------------------
// Formatting
//-----------------------------------------------------------------------------

/**
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
 * @param {NullableDateTime} value
 * @param {ConversionOptions} [options={}]
 */
export function formatDateTime(value, options = {}) {
    if (!value) {
        return "";
    }
    const format = options.format || localization.dateTimeFormat;
    return value.setZone(options.tz || "default").toFormat(format);
}

/**
 * Format a DateTime to a locale date string (e.g. "Jan 31, 2024").
 * Current year is omitted.
 *
 * @param {NullableDateTime} value
 */
export function toLocaleDateString(value) {
    if (!value) {
        return "";
    }
    const format = { ...DateTime.DATE_MED };
    if (today().year === value.year) {
        delete format.year;
    }
    return value.toLocaleString(format);
}

/**
 * Format a DateTime to a locale datetime string (e.g. "Jan 31, 2024, 12:00 AM").
 *
 * @param {NullableDateTime} value
 * @param {ConversionLocalOptions} [options]
 */
export function toLocaleDateTimeString(
    value,
    options = { showDate: true, showTime: true, showSeconds: false },
) {
    if (!value) {
        return "";
    }
    const format = { ...DateTime.DATETIME_MED_WITH_SECONDS };
    if (!options.showSeconds) {
        delete format.second;
    }
    if (options.showDate === false) {
        delete format.day;
        delete format.month;
        delete format.year;
    }
    if (options.showTime === false) {
        delete format.hour;
        delete format.minute;
    }
    if (today().year === value.year) {
        delete format.year;
    }
    return value.setZone(options.tz || "default").toLocaleString(format);
}

/**
 * Converts duration in seconds to human-readable format.
 *
 * @param {number} seconds
 * @param {boolean} showFullDuration
 * @returns {string}
 */
export function formatDuration(seconds, showFullDuration) {
    const displayStyle = showFullDuration ? "long" : "narrow";
    const numberOfValuesToDisplay = showFullDuration ? 2 : 1;
    const durationKeys = ["years", "months", "days", "hours", "minutes"];

    if (seconds < 60) {
        seconds = 60;
    }
    seconds -= seconds % 60;

    let duration = /** @type {any} */ (luxon).Duration.fromObject({
        seconds: seconds,
    }).shiftTo(...durationKeys);
    duration = duration.shiftTo(...durationKeys.filter((key) => duration.get(key)));
    const durationSplit = duration.toHuman({ unitDisplay: displayStyle }).split(",");

    if (
        !showFullDuration &&
        duration.loc.locale.includes("en") &&
        duration.months > 0
    ) {
        durationSplit[0] = durationSplit[0].replace("m", "M");
    }
    return durationSplit.slice(0, numberOfValuesToDisplay).join(",");
}

//-----------------------------------------------------------------------------
// Parsing
//-----------------------------------------------------------------------------

/**
 * @param {string} value
 * @param {ConversionOptions} [options={}]
 */
export function parseDate(value, options = {}) {
    const parsed = parseDateTime(value, {
        ...options,
        format: options.format || localization.dateFormat,
    });
    return parsed && parsed.startOf("day");
}

/**
 * Parses a string value to a Luxon DateTime object.
 * Tries multiple strategies: user format, smart date input, partial formats, ISO, SQL.
 *
 * @param {string} value
 * @param {ConversionOptions} [options={}]
 * @returns {NullableDateTime}
 */
export function parseDateTime(value, options = {}) {
    if (!value) {
        return false;
    }

    const fmt = options.format || localization.dateTimeFormat;
    const parseOpts = {
        setZone: true,
        zone: options.tz || "default",
    };
    const switchToLatin =
        Settings.defaultNumberingSystem !== "latn" && /[0-9]/.test(value);

    if (switchToLatin) {
        parseOpts.numberingSystem = "latn";
    }

    let result = DateTime.fromFormat(value, fmt, parseOpts);

    if (!isValidDate(result)) {
        result = parseSmartDateInput(value);
    }

    if (!isValidDate(result)) {
        const fmtWoZero = stripAlphaDupes(fmt);
        result = DateTime.fromFormat(value, fmtWoZero, parseOpts);
    }

    if (!isValidDate(result)) {
        const digitList = value.split(nonDigitRegex).filter(Boolean);
        const fmtList = fmt.split(nonAlphaRegex).filter(Boolean);
        const valWoSeps = digitList.join("");

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

    if (!isValidDate(result)) {
        const valueDigits = value.replace(nonDigitRegex, "");
        if (valueDigits.length > 4) {
            result = DateTime.fromISO(value, parseOpts);
            if (!isValidDate(result)) {
                result = DateTime.fromSQL(value, parseOpts);
            }
        }
    }

    if (!isValidDate(result)) {
        throw new ConversionError(_t("'%s' is not a correct date or datetime", value));
    }

    if (switchToLatin) {
        result = result.reconfigure({
            numberingSystem: Settings.defaultNumberingSystem,
        });
    }

    return result.setZone(options.tz || "default");
}
