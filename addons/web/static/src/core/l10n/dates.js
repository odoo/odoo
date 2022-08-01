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
 * @returns {DateTime|false} Luxon datetime object (in the UTC timezone)
 */
function parseSmartDateInput(value) {
    const match = smartDateRegex.exec(value);
    if (match) {
        let date = DateTime.utc();
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

// -----------------------------------------------------------------------------
// Formatting
// -----------------------------------------------------------------------------

/**
 * Formats a DateTime object to a date string
 *
 * `options.timezone` is defaulted to false on dates since we assume they
 * shouldn't be affected by timezones like datetimes.
 *
 * @see formatDateTime
 * @returns {string}
 */
export function formatDate(value, options = {}) {
    return formatDateTime(value, {
        timezone: false, // Timezone should never alter a 'date' value.
        ...options,
        format: options.format || localization.dateFormat,
    });
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
 * @param {boolean} [options.timezone=true]
 *  - True = input will be set in local time before being formatted.
 *  - False = input will be set in UTC time before being formatted.
 *
 *  Default=true.
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
    const zone = !("timezone" in options) || options.timezone ? "default" : "utc";
    value = value.setZone(zone, { keepLocaltime: options.timezone });
    return value.toFormat(format, { numberingSystem });
}

// -----------------------------------------------------------------------------
// Parsing
// -----------------------------------------------------------------------------

/**
 * Parses a string value to a Luxon DateTime object.
 *
 * `options.timezone` is defaulted to false on dates since we assume they
 * shouldn't be affected by timezones like datetimes.
 *
 * @see parseDateTime (Note: since we're only interested by the date itself, the
 *  returned value will always be set at the start of the day)
 * @returns {DateTime | false} Luxon DateTime object
 */
export function parseDate(value, options = {}) {
    if (!value) {
        return false;
    }
    return parseDateTime(value, { timezone: false, ...options }).startOf("day");
}

/**
 * Parses a string value to a Luxon DateTime object.
 *
 * @param {string} value value to parse.
 *  - Value can take the form of a smart date:
 *    e.g. "+3w" for three weeks from now.
 *    (`options.format` and `options.timezone` are ignored in this case)
 *
 *  - If value cannot be parsed within the provided format,
 *    ISO8601 and SQL formats are then tried.
 *
 * @param {object} options
 * @param {string} [options.format]
 *  Provided format used to parse the input value.
 *
 *  Default=the session localization format
 *
 * @param {boolean} [options.timezone=false]
 *  - True = input value is considered being in localtime.
 *  - False = input value is considered being in utc time, and the returned
 *            value will have the UTC zone.
 *
 *  NB: ISO strings containing timezone information
 *      will have priority over this option.
 *
 *  Default=false.
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
 * @returns {DateTime | false} Luxon DateTime object
 */
export function parseDateTime(value, options = {}) {
    if (!value) {
        return false;
    }

    const fmt = options.format || localization.dateTimeFormat;
    const parseOpts = {
        setZone: true,
        zone: options.timezone ? "default" : "utc",
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

    return options.timezone ? result : result.toUTC();
}

/**
 * Returns a date object parsed from the given serialized string.
 * @param {string} value
 * @returns {DateTime | false}
 */
export function deserializeDate(value) {
    return DateTime.fromSQL(value, { zone: "utc", numberingSystem: "latn" });
}

/**
 * Returns a datetime object parsed from the given serialized string.
 * @param {string} value
 * @returns {DateTime | false}
 */
export function deserializeDateTime(value) {
    return DateTime.fromSQL(value, { zone: "utc", numberingSystem: "latn" });
}

/**
 * Returns a serialized string representing the given date.
 * @param {DateTime} value
 * @returns {string}
 */
export function serializeDate(value) {
    return value.setZone("utc").toFormat(SERVER_DATE_FORMAT, { numberingSystem: "latn" });
}

/**
 * Returns a serialized string representing the given datetime.
 * @param {DateTime} value
 * @returns {string}
 */
export function serializeDateTime(value) {
    return value.setZone("utc").toFormat(SERVER_DATETIME_FORMAT, { numberingSystem: "latn" });
}
