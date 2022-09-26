/** @odoo-module **/

import { formatDate, formatDateTime } from "@web/core/l10n/dates";
import { localization as l10n } from "@web/core/l10n/localization";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { escape, intersperse, nbsp, sprintf } from "@web/core/utils/strings";
import { isBinarySize } from "@web/core/utils/binary";
import { session } from "@web/session";

const { markup } = owl;

// -----------------------------------------------------------------------------
// Helpers
// -----------------------------------------------------------------------------

/**
 * Inserts "thousands" separators in the provided number.
 *
 * @private
 * @param {string} string representing integer number
 * @param {string} [thousandsSep=","] the separator to insert
 * @param {number[]} [grouping=[]]
 *   array of relative offsets at which to insert `thousandsSep`.
 *   See `strings.intersperse` method.
 * @returns {string}
 */
function insertThousandsSep(number, thousandsSep = ",", grouping = []) {
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
    const unitSymbols = _t("kMGTPE").toString();
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

function humanSize(value) {
    if (!value) {
        return "";
    }
    const suffix = value < 1024 ? " " + _t("Bytes") : "b";
    return (
        humanNumber(value, {
            decimals: 2,
        }) + suffix
    );
}

// -----------------------------------------------------------------------------
// Exports
// -----------------------------------------------------------------------------

/**
 * @param {string} [value] base64 representation of the binary
 * @returns {string}
 */
export function formatBinary(value) {
    if (!isBinarySize(value)) {
        // Computing approximate size out of base64 encoded string
        // http://en.wikipedia.org/wiki/Base64#MIME
        return humanSize(value.length / 1.37);
    }
    // already bin_size
    return value;
}

/**
 * @param {boolean} value
 * @returns {string}
 */
export function formatBoolean(value) {
    return markup(`
        <div class="o-checkbox d-inline-block me-2">
            <input id="boolean_checkbox" type="checkbox" class="form-check-input" disabled ${
                value ? "checked" : ""
            }/>
            <label for="boolean_checkbox" class="form-check-label"/>
        </div>`);
}

/**
 * Returns a string representing a char.  If the value is false, then we return
 * an empty string.
 *
 * @param {string|false} value
 * @param {Object} [options] additional options
 * @param {boolean} [options.escape=false] if true, escapes the formatted value
 * @param {boolean} [options.isPassword=false] if true, returns '********'
 *   instead of the formatted value
 * @returns {string}
 */
export function formatChar(value, options) {
    value = typeof value === "string" ? value : "";
    if (options && options.isPassword) {
        return "*".repeat(value ? value.length : 0);
    }
    if (options && options.escape) {
        value = escape(value);
    }
    return value;
}

/**
 * Returns a string representing a float.  The result takes into account the
 * user settings (to display the correct decimal separator).
 *
 * @param {number | false} value the value that should be formatted
 * @param {Object} [options]
 * @param {number[]} [options.digits] the number of digits that should be used,
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
    if (options.digits && options.digits[1] !== undefined) {
        precision = options.digits[1];
    } else {
        precision = 2;
    }
    const formatted = (value || 0).toFixed(precision).split(".");
    formatted[0] = insertThousandsSep(formatted[0], thousandsSep, grouping);
    if (options.noTrailingZeros) {
        formatted[1] = formatted[1].replace(/0+$/, "");
    }
    return formatted[1] ? formatted.join(decimalPoint) : formatted[0];
}

/**
 * Returns a string representing a float value, from a float converted with a
 * factor.
 *
 * @param {number | false} value
 * @param {Object} [options]
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
 * @param {number | false} value
 * @param {Object} [options]
 * @param {boolean} [options.noLeadingZeroHour] if true, format like 1:30 otherwise, format like 01:30
 * @param {boolean} [options.displaySeconds] if true, format like ?1:30:00 otherwise, format like ?1:30
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
    // Although looking quite overkill, the following line ensures that we do
    // not have float issues while still considering that 59s is 00:00.
    let min = Math.floor((Math.round((value % 1) * 100) / 100) * 60);
    if (min === 60) {
        min = 0;
        hour = hour + 1;
    }
    min = `${min}`.padStart(2, "0");
    if (!options.noLeadingZeroHour) {
        hour = `${hour}`.padStart(2, "0");
    }
    let sec = "";
    if (options.displaySeconds) {
        sec = ":" + `${Math.round((value % 1) * 3600) - min * 60}`.padStart(2, "0");
    }
    return `${isNegative ? "-" : ""}${hour}:${min}${sec}`;
}

/**
 * Returns a string representing an integer.  If the value is false, then we
 * return an empty string.
 *
 * @param {number | false | null} value
 * @param {Object} [options]
 * @param {boolean} [options.humanReadable] if true, large numbers are formatted
 *   to a human readable format.
 * @param {boolean} [options.isPassword=false] if returns true, acts like
 * @param {string} [options.thousandsSep] thousands separator to insert
 * @param {number[]} [options.grouping] array of relative offsets at which to
 *   insert `thousandsSep`. See `insertThousandsSep` method.
 * @returns {string}
 */
export function formatInteger(value, options = {}) {
    if (value === false || value === null) {
        return "";
    }
    if (options.isPassword) {
        return "*".repeat(value.length);
    }
    if (options.humanReadable) {
        return humanNumber(value, options);
    }
    const grouping = options.grouping || l10n.grouping;
    const thousandsSep = "thousandsSep" in options ? options.thousandsSep : l10n.thousandsSep;
    return insertThousandsSep(value.toFixed(0), thousandsSep, grouping);
}

/**
 * Returns a string representing a many2one value. The value is expected to be
 * either `false` or an array in the form [id, display_name]. The returned
 * value will then be the display name of the given value, or an empty string
 * if the value is false.
 *
 * @param {[number, string] | false} value
 * @param {Object} [options] additional options
 * @param {boolean} [options.escape=false] if true, escapes the formatted value
 * @returns {string}
 */
export function formatMany2one(value, options) {
    if (!value) {
        value = "";
    } else {
        value = value[1] || "";
    }
    if (options && options.escape) {
        value = encodeURIComponent(value);
    }
    return value;
}

/**
 * Returns a string representing a one2many or many2many value. The value is
 * expected to be either `false` or an array of ids. The returned value will
 * then be the count of ids in the given value in the form "x record(s)".
 *
 * @param {number[] | false} value
 * @returns {string}
 */
export function formatX2many(value) {
    const count = value.currentIds.length;
    if (count === 0) {
        return _t("No records");
    } else if (count === 1) {
        return _t("1 record");
    } else {
        return sprintf(_t("%s records"), count);
    }
}

/**
 * Returns a string representing a monetary value. The result takes into account
 * the user settings (to display the correct decimal separator, currency, ...).
 *
 * @param {number | false} value the value that should be formatted
 * @param {Object} [options]
 *   additional options to override the values in the python description of the
 *   field.
 * @param {number} [options.currencyId] the id of the 'res.currency' to use
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
    // Monetary fields want to display nothing when the value is unset.
    // You wouldn't want a value of 0 euro if nothing has been provided.
    if (value === false) {
        return "";
    }

    let currencyId = options.currencyId;
    if (!currencyId && options.data) {
        const currencyField =
            options.currencyField ||
            (options.field && options.field.currency_field) ||
            "currency_id";
        const dataValue = options.data[currencyField];
        currencyId = Array.isArray(dataValue) ? dataValue[0] : dataValue;
    }
    const currency = session.currencies[currencyId];
    const digits = (currency && currency.digits) || options.digits;

    let formattedValue;
    if (options.humanReadable) {
        formattedValue = humanNumber(value, { decimals: digits ? digits[1] : 2 });
    } else {
        formattedValue = formatFloat(value, { digits });
    }

    if (!currency || options.noSymbol) {
        return formattedValue;
    }
    const formatted = [currency.symbol, formattedValue];
    if (currency.position === "after") {
        formatted.reverse();
    }
    return formatted.join(nbsp);
}

/**
 * Returns a string representing the given value (multiplied by 100)
 * concatenated with '%'.
 *
 * @param {number | false} value
 * @param {Object} [options]
 * @param {boolean} [options.noSymbol] if true, doesn't concatenate with "%"
 * @returns {string}
 */
export function formatPercentage(value, options = {}) {
    value = value || 0;
    options = Object.assign({ noTrailingZeros: true, thousandsSep: "" }, options);
    const formatted = formatFloat(value * 100, options);
    return `${formatted}${options.noSymbol ? "" : "%"}`;
}

/**
 * Returns a string representing the value of the python properties field
 * or a properties definition field (see fields.py@Properties).
 *
 * @param {array|false} value
 * @param {Object} [field]
 *        a description of the field (note: this parameter is ignored)
 */
function formatProperties(value, field) {
    if (!value || !value.length) {
        return "";
    }
    return value.map((property) => property["string"]).join(", ");
}

/**
 * Returns a string representing the value of the reference field.
 *
 * @param {Object|false} value Object with keys "resId" and "displayName"
 * @param {Object} [options={}]
 * @returns {string}
 */
export function formatReference(value, options) {
    return formatMany2one(value ? [value.resId, value.displayName] : false, options);
}

/**
 * Returns a string of the value of the selection.
 *
 * @param {Object} [options={}]
 * @param {[string, string][]} [options.selection]
 * @param {Object} [options.field]
 * @returns {string}
 */
export function formatSelection(value, options = {}) {
    const selection = options.selection || (options.field && options.field.selection) || [];
    const option = selection.find((option) => option[0] === value);
    return option ? option[1] : "";
}

/**
 * Returns the value or an empty string if it's falsy.
 *
 * @param {string | false} value
 * @returns {string}
 */
export function formatText(value) {
    return value || "";
}

registry
    .category("formatters")
    .add("binary", formatBinary)
    .add("boolean", formatBoolean)
    .add("char", formatChar)
    .add("date", formatDate)
    .add("datetime", formatDateTime)
    .add("float", formatFloat)
    .add("float_factor", formatFloatFactor)
    .add("float_time", formatFloatTime)
    .add("html", (value) => value)
    .add("integer", formatInteger)
    .add("many2one", formatMany2one)
    .add("many2one_reference", formatInteger)
    .add("one2many", formatX2many)
    .add("many2many", formatX2many)
    .add("monetary", formatMonetary)
    .add("percentage", formatPercentage)
    .add("properties", formatProperties)
    .add("properties_definition", formatProperties)
    .add("reference", formatReference)
    .add("selection", formatSelection)
    .add("text", formatText);
