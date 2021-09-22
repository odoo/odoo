/** @odoo-module **/

import { parseDate, parseDateTime } from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";
import { registry } from "@web/core/registry";
import { escapeRegExp } from "@web/core/utils/strings";
import { session } from "@web/session";

// -----------------------------------------------------------------------------
// Helpers
// -----------------------------------------------------------------------------

/**
 * Parses a string into a number.
 *
 * @param {string} value
 * @param {Object} options - additional options
 * @param {string|RegExp} [options.thousandsSep] - the thousands separator used in the value
 * @param {string|RegExp} [options.decimalPoint] - the decimal point used in the value
 * @returns {number}
 */
function parseNumber(value, options = {}) {
    // a number can have the thousand separator multiple times. ex: 1,000,000.00
    value = value.replaceAll(options.thousandsSep || ",", "");
    // a number only have one decimal separator
    value = value.replace(options.decimalPoint || ".", ".");
    return Number(value);
}

// -----------------------------------------------------------------------------
// Exports
// -----------------------------------------------------------------------------

export class InvalidNumberError extends Error {}

/**
 * Try to extract a float from a string. The localization is considered in the process.
 *
 * @param {string} value
 * @returns {number} a float
 */
export function parseFloat(value) {
    const thousandsSepRegex = new RegExp(escapeRegExp(localization.thousandsSep), "g");
    const decimalPointRegex = new RegExp(escapeRegExp(localization.decimalPoint), "g");
    const parsed = parseNumber(value, {
        thousandsSep: thousandsSepRegex,
        decimalPoint: decimalPointRegex,
    });
    if (isNaN(parsed)) {
        throw new InvalidNumberError(`"${value}" is not a correct number`);
    }
    return parsed;
}

/**
 * Try to extract a float time from a string. The localization is considered in the process.
 * The float time can have two formats: float or integer:integer.
 *
 * @param {string} value
 * @returns {number} a float
 */
export function parseFloatTime(value) {
    let sign = 1;
    if (value[0] === "-") {
        value = value.slice(1);
        sign = -1;
    }
    const values = value.split(":");
    if (values.length > 2) {
        throw new InvalidNumberError(`"${value}" is not a correct number`);
    }
    if (values.length === 1) {
        return sign * parseFloat(value);
    }
    const hours = parseInteger(values[0]);
    const minutes = parseInteger(values[1]);
    return sign * (hours + minutes / 60);
}

/**
 * Try to extract an integer from a string. The localization is considered in the process.
 *
 * @param {string} value
 * @returns {number} an integer
 */
export function parseInteger(value) {
    const thousandsSepRegex = new RegExp(escapeRegExp(localization.thousandsSep), "g");
    const decimalPointRegex = new RegExp(escapeRegExp(localization.decimalPoint), "g");
    const parsed = parseNumber(value, {
        thousandsSep: thousandsSepRegex,
        decimalPoint: decimalPointRegex,
    });
    if (!Number.isInteger(parsed)) {
        throw new InvalidNumberError(`"${value}" is not a correct number`);
    }
    return parsed;
}

/**
 * Try to extract a float from a string and unconvert it with a conversion factor of 100.
 * The localization is considered in the process.
 * The percentage can have two formats: float or float%.
 *
 * @param {string} value
 * @returns {number} float
 */
export function parsePercentage(value) {
    if (value[value.length - 1] === "%") {
        value = value.slice(0, value.length - 1);
    }
    return parseFloat(value) / 100;
}

/**
 * Try to extract a monetary value from a string. The localization is considered in the process.
 * The monetary value can have the formats sym$&nbsp;float, float$&nbsp;sym or float
 * where $&nbsp; is a non breaking space and sym is a currency symbol.
 * If a symbol is found it must correspond to the default currency symbol or to the
 * symbol of the currency whose id is passed in options.
 *
 * @param {string} value
 * @param {Object} [options={}]
 * @param {number} [options.currencyId]
 * @returns {number} float
 */
export function parseMonetary(value, options = {}) {
    const values = value.split("&nbsp;");
    if (values.length === 1) {
        return parseFloat(value);
    }
    let currency;
    if (options.currencyId) {
        currency = session.currencies[options.currencyId];
    } else {
        currency = Object.values(session.currencies)[0];
    }
    const symbolIndex = values.findIndex((v) => v === currency.symbol);
    if (symbolIndex === -1) {
        throw new InvalidNumberError(`"${value}" is not a correct number`);
    }
    values.splice(symbolIndex, 1);
    if (values.length !== 1) {
        throw new InvalidNumberError(`"${value}" is not a correct number`);
    }
    return parseFloat(values[0]);
}

registry
    .category("parsers")
    .add("date", parseDate)
    .add("datetime", parseDateTime)
    .add("float", parseFloat)
    .add("float_time", parseFloatTime)
    .add("integer", parseInteger)
    .add("monetary", parseMonetary)
    .add("percentage", parsePercentage);
