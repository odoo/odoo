/** @odoo-module **/

import { localization } from "@web/core/l10n/localization";
import { _t } from "@web/core/l10n/translation";
import { memoize } from "@web/core/utils/functions";
import { sprintf } from "@web/core/utils/strings";

const { DateTime, Settings } = luxon;

const SERVER_DATE_FORMAT = "yyyy-MM-dd";
const SERVER_TIME_FORMAT = "HH:mm:ss";
const SERVER_DATETIME_FORMAT = `${SERVER_DATE_FORMAT} ${SERVER_TIME_FORMAT}`;

// -----------------------------------------------------------------------------
// Helpers
// -----------------------------------------------------------------------------

const alphaRegex = /[a-zA-Z]/g;
const nonAlphaRegex = /[^a-zA-Z]/g;
const nonDigitsRegex = /[^0-9]/g;

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

const luxonToMomentFormatTable = {
    c: "d",
    d: "D",
    o: "DDDD",
    a: "A",
    y: "Y",
};

const smartDateUnits = {
    d: "days",
    m: "months",
    w: "weeks",
    y: "years",
};
const smartDateRegex = new RegExp(`^([+-])(\\d+)([${Object.keys(smartDateUnits).join("")}]?)$`);

/**
 * @param {any} d1
 * @param {any} d2
 * @returns {boolean}
 */
export function areDateEquals(d1, d2) {
    return d1 instanceof DateTime && d2 instanceof DateTime ? d1.equals(d2) : d1 === d2;
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
 * @returns {DateTime|false} Luxon datetime object (in the user's local timezone)
 */
function parseSmartDateInput(value) {
    const match = smartDateRegex.exec(value);
    if (match) {
        let date = DateTime.local();
        const offset = parseInt(match[2], 10);
        const unit = smartDateUnits[match[3] || "d"];
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
 * Enforces some restrictions to a Luxon DateTime object.
 * Returns it if within those restrictions.
 * Returns false otherwise.
 *
 * @param {DateTime | false} date
 * @returns {boolean}
 */
function isValidDateTime(dt) {
    return dt && dt.isValid && dt.year >= 1000 && dt.year < 10000;
}

/**
 * Removes any duplicated alphabetic characters in a given string.
 * Example: "aa-bb-CCcc-ddD xxxx-Yy-ZZ" -> "a-b-Cc-dD x-Yy-Z"
 *
 * @param {string} str
 * @returns {string}
 */
const stripAlphaDupes = memoize(function stripAlphaDupes(str) {
    return str.replace(alphaRegex, (letter, index, str) => {
        return letter === str[index - 1] ? "" : letter;
    });
});

/**
 * Convert Python strftime to escaped luxon.js format.
 *
 * @param {string} value original format
 * @returns {string} valid Luxon format
 */
export const strftimeToLuxonFormat = memoize(function strftimeToLuxonFormat(value) {
    const output = [];
    let inToken = false;
    for (let index = 0; index < value.length; ++index) {
        let character = value[index];
        if (character === "%" && !inToken) {
            inToken = true;
            continue;
        }
        if (character.match(alphaRegex)) {
            if (inToken && normalizeFormatTable[character] !== undefined) {
                character = normalizeFormatTable[character];
            } else {
                character = "[" + character + "]"; // moment.js escape
            }
        }
        output.push(character);
        inToken = false;
    }
    return output.join("");
});

/**
 * Converts a Luxon format to a moment.js format.
 * NB: this is not a complete conversion, only the supported tokens are converted.
 *
 * @param {string} value original format
 * @returns {string} valid moment.js format
 */
export const luxonToMomentFormat = memoize(function luxonToMomentFormat(format) {
    return format.replace(alphaRegex, (match) => {
        return luxonToMomentFormatTable[match] || match;
    });
});

/**
 * Converts a luxon's DateTime object into a moment.js object.
 * NB: the passed object's values will be utilized as is, regardless of its corresponding timezone.
 * So passing a luxon's DateTime having 8 as hours value will result in a moment.js object having
 * also 8 as hours value. But the moment.js object will be in the browser's timezone.
 *
 * @param {DateTime} dt a luxon's DateTime object
 * @returns {moment} a moment.js object in the browser's timezone
 */
export function luxonToMoment(dt) {
    const o = dt.toObject();
    // Note: the month is 0-based in moment.js, but 1-based in luxon.js
    return moment({ ...o, month: o.month - 1 });
}

/**
 * Converts a moment.js object into a luxon's DateTime object.
 * NB: the passed object's values will be utilized as is, regardless of its corresponding timezone.
 * So passing a moment.js object having 8 as hours value will result in a luxon's DateTime object
 * having also 8 as hours value. But the luxon's DateTime object will be in the user's timezone.
 *
 * @param {moment} dt a moment.js object
 * @returns {DateTime} a luxon's DateTime object in the user's timezone
 */
export function momentToLuxon(dt) {
    const o = dt.toObject();
    // Note: the month is 0-based in moment.js, but 1-based in luxon.js
    return DateTime.fromObject({
        year: o.years,
        month: o.months + 1,
        day: o.date,
        hour: o.hours,
        minute: o.minutes,
        second: o.seconds,
        millisecond: o.milliseconds,
    });
}

// -----------------------------------------------------------------------------
// Formatting
// -----------------------------------------------------------------------------

/**
 * Returns true if the given format is a 24-hour format.
 * Returns false otherwise.
 *
 * @param {string} [format=localization.timeFormat]
 * @returns true if the format contains a 24 hour format
 */
export function is24HourFormat(format) {
    return (format || localization.timeFormat).indexOf("H") !== -1;
}

/**
 * Formats a DateTime object to a date string
 *
 * @see formatDateTime
 * @returns {string}
 */
export function formatDate(value, options = {}) {
    if (value === false) {
        return "";
    }
    const format = options.format || localization.dateFormat;
    const numberingSystem = options.numberingSystem || Settings.defaultNumberingSystem || "latn";
    return value.toFormat(format, { numberingSystem });
}

/**
 * Formats a DateTime object to a datetime string
 *
 * @param {DateTime | false} value
 * @param {Object} options
 * @param {string} [options.format]
 *  Provided format used to format the input DateTime object.
 *
 *  Default=the session localization format.
 *
 * @param {string} [options.numberingSystem]
 *  Provided numbering system used to parse the input value.
 *
 * Default=the default numbering system assigned to luxon
 * @see localization_service.js
 *
 * @returns {string}
 */
export function formatDateTime(value, options = {}) {
    if (value === false) {
        return "";
    }
    const format = options.format || localization.dateTimeFormat;
    const numberingSystem = options.numberingSystem || Settings.defaultNumberingSystem || "latn";
    return value.setZone("default").toFormat(format, { numberingSystem });
}

// -----------------------------------------------------------------------------
// Parsing
// -----------------------------------------------------------------------------

/**
 * Parses a string value to a Luxon DateTime object.
 *
 * @see parseDateTime (Note: since we're only interested by the date itself, the
 *  returned value will always be set at the start of the day)
 * @returns {DateTime | false} Luxon DateTime object in user's timezone
 */
export function parseDate(value, options = {}) {
    if (!value) {
        return false;
    }
    return parseDateTime(value, options).startOf("day");
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
 * @param {object} options
 * @param {string} [options.format]
 *  Provided format used to parse the input value.
 *
 *  Default=the session localization format
 *
 * @param {string} [options.locale]
 *  Provided locale used to parse the input value.
 *
 * Default=the session localization locale
 *
 * @param {string} [options.numberingSystem]
 *  Provided numbering system used to parse the input value.
 *
 * Default=the default numbering system assigned to luxon
 * @see localization_service.js
 *
 * @returns {DateTime | false} Luxon DateTime object in user's timezone
 */
export function parseDateTime(value, options = {}) {
    if (!value) {
        return false;
    }

    const fmt = options.format || localization.dateTimeFormat;
    const parseOpts = {
        setZone: true,
        zone: "default",
        locale: options.locale,
        numberingSystem: options.numberingSystem || Settings.defaultNumberingSystem || "latn",
    };

    // Base case: try parsing with the given format and options
    let result = DateTime.fromFormat(value, fmt, parseOpts);

    // Try parsing as a smart date
    if (!isValidDateTime(result)) {
        result = parseSmartDateInput(value);
    }

    // Try parsing with partial date parts
    if (!isValidDateTime(result)) {
        const fmtWoZero = stripAlphaDupes(fmt);
        result = DateTime.fromFormat(value, fmtWoZero, parseOpts);
    }

    // Try parsing with custom shorthand date parts
    if (!isValidDateTime(result)) {
        // Luxon is not permissive regarding delimiting characters in the format.
        // So if the value to parse has less characters than the format, we would
        // try to parse without the delimiting characters.
        const digitList = value.split(nonDigitsRegex).filter(Boolean);
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
    if (!isValidDateTime(result)) {
        // Also try some fallback formats, but only if value counts more than
        // four digit characters as this could get misinterpreted as the time of
        // the actual date.
        const valueDigits = value.replace(nonDigitsRegex, "");
        if (valueDigits.length > 4) {
            result = DateTime.fromISO(value, parseOpts); // ISO8601
            if (!isValidDateTime(result)) {
                result = DateTime.fromSQL(value, parseOpts); // last try: SQL
            }
        }
    }

    // No working parsing methods: throw an error
    if (!isValidDateTime(result)) {
        throw new Error(sprintf(_t("'%s' is not a correct date or datetime"), value));
    }

    return result.setZone("default");
}

/**
 * Returns a date object parsed from the given serialized string.
 * @param {string} value serialized date string, e.g. "2018-01-01"
 * @returns {DateTime} parsed date object in user's timezone
 */
export function deserializeDate(value) {
    return DateTime.fromSQL(value, { zone: "default", numberingSystem: "latn" });
}

/**
 * Returns a datetime object parsed from the given serialized string.
 * @param {string} value serialized datetime string, e.g. "2018-01-01 00:00:00", expressed in UTC
 * @returns {DateTime} parsed datetime object in user's timezone
 */
export function deserializeDateTime(value) {
    return DateTime.fromSQL(value, { zone: "utc", numberingSystem: "latn" }).setZone("default");
}

const dateCache = new WeakMap();
/**
 * Returns a serialized string representing the given date.
 * @param {DateTime} value DateTime object, its timezone does not matter
 * @returns {string} serialized date, ready to be sent to the server
 */
export function serializeDate(value) {
    if (!dateCache.has(value)) {
        dateCache.set(value, value.toFormat(SERVER_DATE_FORMAT, { numberingSystem: "latn" }));
    }
    return dateCache.get(value);
}

const dateTimeCache = new WeakMap();
/**
 * Returns a serialized string representing the given datetime.
 * @param {DateTime} value DateTime object, its timezone does not matter
 * @returns {string} serialized datetime, ready to be sent to the server
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
