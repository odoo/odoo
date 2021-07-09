/** @odoo-module **/

import { formatCurrency } from "@web/core/l10n/currency";
import {
    formatFloat as _formatFloat,
    formatInteger as _formatInteger,
    formatPercentage as _formatPercentage,
    humanNumber,
} from "@web/core/l10n/numbers";
import { registry } from "@web/core/registry";

/**
 * Returns a string representing a float.  The result takes into account the
 * user settings (to display the correct decimal separator).
 *
 * @param {float|false} value the value that should be formatted
 * @param {Object} [field] a description of the field (returned by fields_get
 *   for example).  It may contain a description of the number of digits that
 *   should be used.
 * @param {Object} [options]
 * @param {integer[]} [options.digits] the number of digits that should be used,
 *   instead of the default digits precision in the field.
 * @param {function} [options.humanReadable] function that takes the value in
 *   argument, and if it returns true, the formatter acts like humanNumber
 * @returns {string}
 */
export function formatFloat(value, field, options = {}) {
    if (value === false) {
        return "";
    }
    if (options.humanReadable && options.humanReadable(value)) {
        return humanNumber(value, options);
    }
    let precision;
    if (options.digits) {
        precision = options.digits[1];
    } else if (field && field.digits) {
        precision = field.digits[1];
    } else {
        precision = 2;
    }
    return _formatFloat(value, { precision });
}

/**
 * Returns a string representing a float value, from a float converted with a
 * factor.
 *
 * @param {number} value
 * @param {Object} [field] a description of the field
 * @param {number} [options.factor=1.0] conversion factor
 * @returns {string}
 */
export function formatFloatFactor(value, field, options = {}) {
    if (value === false) {
        return "";
    }
    const factor = options.factor || 1;
    return formatFloat(value * factor, field, options);
}

/**
 * Returns a string representing a time value, from a float.  The idea is that
 * we sometimes want to display something like 1:45 instead of 1.75, or 0:15
 * instead of 0.25.
 *
 * @param {float} value
 * @param {Object} [field] a description of the field
 * @param {Object} [options]
 * @param {boolean} [options.noLeadingZeroHour] if true, format like 1:30
 *   otherwise, format like 01:30
 * @returns {string}
 */
export function formatFloatTime(value, field, options = {}) {
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
 * @param {Object} [field] a description of the field
 * @param {Object} [options]
 * @param {function} [options.humanReadable] function that takes the value in
 *   argument, and if it returns true, the formatter acts like humanNumber
 * @param {boolean} [options.isPassword=false] if returns true, acts like
 * @returns {string}
 */
export function formatInteger(value, field, options = {}) {
    if (value === false) {
        return "";
    }
    if (options.isPassword) {
        return new Array(value.length + 1).join("*");
    }
    if (options.humanReadable && options.humanReadable(value)) {
        return humanNumber(value, options);
    }
    return _formatInteger(value);
}

/**
 * Returns a string representing an many2one.  If the value is false, then we
 * return an empty string. Note that it accepts two types of input parameters:
 * an array, in that case we assume that the many2one value is of the form
 * [id, nameget], and we return the nameget, or it can be an object, and in that
 * case, we assume that it is a record datapoint from a BasicModel.
 *
 * @param {Array|Object|false} value
 * @param {Object} [field] a description of the field
 * @param {{escape?: boolean}} [options] additional options
 * @param {boolean} [options.escape=false] if true, escapes the formatted value
 * @returns {string}
 */
export function formatMany2one(value, field, options) {
    if (!value) {
        value = "";
    } else if (Array.isArray(value)) {
        // value is a pair [id, nameget]
        value = value[1];
    } else {
        // value is a datapoint, so we read its display_name field, which
        // may in turn be a datapoint (if the name field is a many2one)
        while (value.data) {
            value = value.data.display_name || "";
        }
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
 * @param {integer[]} [options.digits] see @formatCurrency
 * @param {integer[]} [options.humanReadable] see @formatCurrency
 * @param {integer[]} [options.noSymbol] see @formatCurrency
 * @returns {string}
 */
export function formatMonetary(value, field, options = {}) {
    let currencyId = options.currencyId;
    if (!currencyId && options.data) {
        const currencyField =
            options.currencyField || (field && field.currency_field) || "currency_id";
        currencyId = options.data[currencyField] && options.data[currencyField].res_id;
    }
    return formatCurrency(value, currencyId, options);
}

/**
 * Returns a string representing the given value (multiplied by 100)
 * concatenated with '%'.
 *
 * @param {number | false} value
 * @param {Object} [field]
 * @param {Object} [options]
 * @param {boolean} [options.noSymbol] if true, doesn't concatenate with "%"
 * @returns {string}
 */
export function formatPercentage(value, field, options = {}) {
    if (options.humanReadable && options.humanReadable(value * 100)) {
        value = value || 0;
        return `${humanNumber(value * 100, options)}${options.noSymbol ? "" : "%"}`;
    }
    return _formatPercentage(value, options);
}

registry
    .category("formatters")
    .add("float", formatFloat)
    .add("float_factor", formatFloatFactor)
    .add("float_time", formatFloatTime)
    .add("integer", formatInteger)
    .add("many2one", formatMany2one)
    .add("monetary", formatMonetary)
    .add("percentage", formatPercentage);
