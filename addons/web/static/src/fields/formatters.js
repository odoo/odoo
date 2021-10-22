/** @odoo-module **/

import { formatDate, formatDateTime } from "@web/core/l10n/dates";
import { localization as l10n } from "@web/core/l10n/localization";
import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { intersperse } from "@web/core/utils/strings";
import { session } from "@web/session";

// -----------------------------------------------------------------------------
// Helpers
// -----------------------------------------------------------------------------

/**
 * Inserts "thousands" separators in the provided number.
 *
 * @private
 * @param {string} string representing integer number
 * @param {string} [thousandsSep=","] the separator to insert
 * @param {number[]} [grouping=[3,0]]
 *   array of relative offsets at which to insert `thousandsSep`.
 *   See `strings.intersperse` method.
 * @returns {string}
 */
function insertThousandsSep(number, thousandsSep = ",", grouping = [3, 0]) {
    const negative = number[0] === "-";
    number = negative ? number.slice(1) : number;
    return (negative ? "-" : "") + intersperse(number, grouping, thousandsSep);
}

/**
 * Format a number to a human readable format. For example, 3000 could become 3k.
 * Or massive number can use the scientific exponential notation.
 *
 * @private
 * @param {number} number to format
 * @param {Object} [options] Options to format
 * @param {number} [options.decimals=0] number of decimals to use
 *    if minDigits > 1 is used and effective on the number then decimals
 *    will be shrunk to zero, to avoid displaying irrelevant figures ( 0.01 compared to 1000 )
 * @param {number} [options.minDigits=1]
 *    the minimum number of digits to preserve when switching to another
 *    level of thousands (e.g. with a value of '2', 4321 will still be
 *    represented as 4321 otherwise it will be down to one digit (4k))
 * @returns {string}
 */
function humanNumber(number, options = { decimals: 0, minDigits: 1 }) {
    const decimals = options.decimals || 0;
    const minDigits = options.minDigits || 1;
    const d2 = Math.pow(10, decimals);
    const numberMagnitude = +number.toExponential().split("e+")[1];
    number = Math.round(number * d2) / d2;
    // the case numberMagnitude >= 21 corresponds to a number
    // better expressed in the scientific format.
    if (numberMagnitude >= 21) {
        // we do not use number.toExponential(decimals) because we want to
        // avoid the possible useless O decimals: 1e.+24 preferred to 1.0e+24
        number = Math.round(number * Math.pow(10, decimals - numberMagnitude)) / d2;
        return `${number}e+${numberMagnitude}`;
    }
    // note: we need to call toString here to make sure we manipulate the resulting
    // string, not an object with a toString method.
    const unitSymbols = _lt("kMGTPE").toString();
    const sign = Math.sign(number);
    number = Math.abs(number);
    let symbol = "";
    for (let i = unitSymbols.length; i > 0; i--) {
        const s = Math.pow(10, i * 3);
        if (s <= number / Math.pow(10, minDigits - 1)) {
            number = Math.round((number * d2) / s) / d2;
            symbol = unitSymbols[i - 1];
            break;
        }
    }
    const { decimalPoint, grouping, thousandsSep } = l10n;

    // determine if we should keep the decimals (we don't want to display 1,020.02k for 1020020)
    const decimalsToKeep = number >= 1000 ? 0 : decimals;
    number = sign * number;
    const [integerPart, decimalPart] = number.toFixed(decimalsToKeep).split(".");
    const int = insertThousandsSep(integerPart, thousandsSep, grouping);
    if (!decimalPart) {
        return int + symbol;
    }
    return int + decimalPoint + decimalPart + symbol;
}

// -----------------------------------------------------------------------------
// Exports
// -----------------------------------------------------------------------------

/**
 * Returns a string representing a float.  The result takes into account the
 * user settings (to display the correct decimal separator).
 *
 * @param {float|false} value the value that should be formatted
 * @param {Object} [options]
 * @param {Object} [options.field] a description of the field (returned by
 *   fields_get for example).  It may contain a description of the number of
 *   digits that should be used.
 * @param {integer[]} [options.digits] the number of digits that should be used,
 *   instead of the default digits precision in the field.
 * @param {boolean} [options.humanReadable] if true, large numbers are formatted
 *   to a human readable format.
 * @param {string} [options.decimalPoint] decimal separating character
 * @param {string} [options.thousandsSep] thousands separator to insert
 * @param {number[]} [options.grouping] array of relative offsets at which to
 *   insert `thousandsSep`. See `insertThousandsSep` method.
 * @param {boolean} [options.noTrailingZeros=false] if true, the decimal part
 *   won't contain unnecessary trailing zeros.
 * @returns {string}
 */
export function formatFloat(value, options = {}) {
    if (value === false) {
        return "";
    }
    if (options.humanReadable) {
        return humanNumber(value, options);
    }
    const grouping = options.grouping || l10n.grouping;
    const thousandsSep = "thousandsSep" in options ? options.thousandsSep : l10n.thousandsSep;
    const decimalPoint = "decimalPoint" in options ? options.decimalPoint : l10n.decimalPoint;
    let precision;
    if (options.digits) {
        precision = options.digits[1];
    } else if (options.field && options.field.digits) {
        precision = options.field.digits[1];
    } else {
        precision = 2;
    }
    const formatted = (value || 0).toFixed(precision || 2).split(".");
    formatted[0] = insertThousandsSep(formatted[0], thousandsSep, grouping);
    if (options.noTrailingZeros) {
        formatted[1] = formatted[1].replace(/0+$/, "");
    }
    return formatted[1].length ? formatted.join(decimalPoint) : formatted[0];
}

/**
 * Returns a string representing a float value, from a float converted with a
 * factor.
 *
 * @param {number|false} value
 * @param {Object} [options]
 * @param {Object} [options.field] a description of the field
 * @param {number} [options.factor=1.0] conversion factor
 * @returns {string}
 */
export function formatFloatFactor(value, options = {}) {
    if (value === false) {
        return "";
    }
    const factor = options.factor || 1;
    return formatFloat(value * factor, options);
}

/**
 * Returns a string representing a time value, from a float.  The idea is that
 * we sometimes want to display something like 1:45 instead of 1.75, or 0:15
 * instead of 0.25.
 *
 * @param {number|false} value
 * @param {Object} [options]
 * @param {Object} [options.field] a description of the field
 * @param {boolean} [options.noLeadingZeroHour] if true, format like 1:30
 *   otherwise, format like 01:30
 * @returns {string}
 */
export function formatFloatTime(value, options = {}) {
    if (value === false) {
        return "";
    }
    const isNegative = value < 0;
    if (isNegative) {
        value = Math.abs(value);
    }
    let hour = Math.floor(value);
    let min = Math.round((value % 1) * 60);
    if (min === 60) {
        min = 0;
        hour = hour + 1;
    }
    min = `${min}`.padStart(2, "0");
    if (!options.noLeadingZeroHour) {
        hour = `${hour}`.padStart(2, "0");
    }
    return `${isNegative ? "-" : ""}${hour}:${min}`;
}

/**
 * Returns a string representing an integer.  If the value is false, then we
 * return an empty string.
 *
 * @param {integer|false} value
 * @param {Object} [options]
 * @param {Object} [options.field] a description of the field
 * @param {boolean} [options.humanReadable] if true, large numbers are formatted
 *   to a human readable format.
 * @param {boolean} [options.isPassword=false] if returns true, acts like
 * @param {string} [options.thousandsSep] thousands separator to insert
 * @param {number[]} [options.grouping] array of relative offsets at which to
 *   insert `thousandsSep`. See `insertThousandsSep` method.
 * @returns {string}
 */
export function formatInteger(value, options = {}) {
    if (value === false) {
        return "";
    }
    if (options.isPassword) {
        return new Array(value.length + 1).join("*");
    }
    if (options.humanReadable) {
        return humanNumber(value, options);
    }
    const grouping = options.grouping || l10n.grouping;
    const thousandsSep = "thousandsSep" in options ? options.thousandsSep : l10n.thousandsSep;
    return insertThousandsSep(value.toFixed(0), thousandsSep, grouping);
}

/**
 * Returns a string representing an many2one.  If the value is false, then we
 * return an empty string. Note that it accepts two types of input parameters:
 * an array, in that case we assume that the many2one value is of the form
 * [id, nameget], and we return the nameget, or it can be an object, and in that
 * case, we assume that it is a record datapoint from a BasicModel.
 *
 * @param {Array|Object|false} value
 * @param {Object} [options] additional options
 * @param {Object} [options.field] a description of the field
 * @param {boolean} [options.escape=false] if true, escapes the formatted value
 * @returns {string}
 */
export function formatMany2one(value, options) {
    if (!value) {
        value = "";
    } else {
        value = value[1];
    }
    if (options && options.escape) {
        value = encodeURIComponent(value);
    }
    return value;
}

/**
 * Returns a string representing a monetary value. The result takes into account
 * the user settings (to display the correct decimal separator, currency, ...).
 *
 * @param {float|false} value the value that should be formatted
 * @param {Object} [field]
 *   a description of the field (returned by fields_get for example). It may
 *   contain a description of the number of digits that should be used.
 * @param {Object} [options]
 *   additional options to override the values in the python description of the
 *   field.
 * @param {integer} [options.currencyId] the id of the 'res.currency' to use
 * @param {string} [options.currencyField] the name of the field whose value is
 *   the currency id (ignored if options.currency_id).
 *   Note: if not given it will default to the field "currency_field" value or
 *   on "currency_id".
 * @param {Object} [options.data] a mapping of field names to field values,
 *   required with options.currencyField
 * @param {boolean} [options.noSymbol] this currency has not a sympbol
 * @param {boolean} [options.humanReadable] if true, large numbers are formatted
 *   to a human readable format.
 * @param {[number, number]} [options.digits] the number of digits that should
 *   be used, instead of the default digits precision in the field.  The first
 *   number is always ignored (legacy constraint)
 * @returns {string}
 */
export function formatMonetary(value, options = {}) {
    let currencyId = options.currencyId;
    if (!currencyId && options.data) {
        const currencyField =
            options.currencyField ||
            (options.field && options.field.currency_field) ||
            "currency_id";
        currencyId = options.data[currencyField] && options.data[currencyField].res_id;
    }
    const currency = session.currencies[currencyId];
    const digits = (currency && currency.digits) || options.digits;

    let formatted;
    if (options.humanReadable) {
        formatted = humanNumber(value, { decimals: digits ? digits[1] : 2 });
    } else {
        formatted = formatFloat(value, { digits });
    }

    if (!currency || options.noSymbol) {
        return formatted;
    }
    if (currency.position === "after") {
        return `${formatted} ${currency.symbol}`;
    } else {
        return `${currency.symbol} ${formatted}`;
    }
}

/**
 * Returns a string representing the given value (multiplied by 100)
 * concatenated with '%'.
 *
 * @param {number | false} value
 * @param {Object} [options]
 * @param {Object} [options.field] a description of the field
 * @param {boolean} [options.noSymbol] if true, doesn't concatenate with "%"
 * @returns {string}
 */
export function formatPercentage(value, options = {}) {
    value = value || 0;
    options = Object.assign({ noTrailingZeros: true, thousandsSep: "" }, options);
    const formatted = formatFloat(value * 100, options);
    return `${formatted}${options.noSymbol ? "" : "%"}`;
}

registry
    .category("formatters")
    .add("date", formatDate)
    .add("datetime", formatDateTime)
    .add("float", formatFloat)
    .add("float_factor", formatFloatFactor)
    .add("float_time", formatFloatTime)
    .add("integer", formatInteger)
    .add("many2one", formatMany2one)
    .add("monetary", formatMonetary)
    .add("percentage", formatPercentage);
