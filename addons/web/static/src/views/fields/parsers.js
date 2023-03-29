/** @odoo-module **/

import { parseDate, parseDateTime } from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";
import { evaluateExpr } from "@web/core/py_js/py";
import { registry } from "@web/core/registry";
import { escapeRegExp } from "@web/core/utils/strings";

// -----------------------------------------------------------------------------
// Helpers
// -----------------------------------------------------------------------------

function evaluateMathematicalExpression(expr, context = {}) {
    // remove extra space
    var val = expr.replace(new RegExp(/( )/g), "");
    var safeEvalString = "";
    for (let v of val.split(new RegExp(/([-+*/()^])/g))) {
        if (!["+", "-", "*", "/", "(", ")", "^"].includes(v) && v.length) {
            // check if this is a float and take into account user delimiter preference
            v = parseFloat(v);
        }
        if (v === "^") {
            v = "**";
        }
        safeEvalString += v;
    }
    return evaluateExpr(safeEvalString, context);
}

/**
 * Parses a string into a number.
 *
 * @param {string} value
 * @param {Object} options - additional options
 * @param {string|RegExp} options.thousandsSep - the thousands separator used in the value
 * @param {string|RegExp} options.decimalPoint - the decimal point used in the value
 * @param {boolean} options.truncate
 * @returns {number}
 */
export function parseNumber(value, options = {}) {
    const { thousandsSep, decimalPoint, truncate } = options;
    let parsed = NaN;
    if (value.startsWith("=")) {
        parsed = evaluateMathematicalExpression(value.substring(1));
    } else {
        if (!(thousandsSep == null && decimalPoint == null)) {
            parsed = strictParseNumber(value, options);
        }
        if (isNaN(parsed)) {
            parsed = lenientParseNumber(value, options);
        }
    }
    if (isNaN(parsed)) {
        throw new Error(`Unable to parse: '${value}'`);
    }
    return truncate ? Math.trunc(parsed) : parsed;
}

function strictParseNumber(value, options) {
    const { thousandsSep, decimalPoint } = options;
    // A whitespace thousands separator is equivalent to any whitespace character.
    // E.g. "1  000 000" should be parsed as 1000000 even if the
    // thousands separator is nbsp.
    const thousandsSepRegex = thousandsSep.match(/\s+/)
        ? /\s+/g
        : new RegExp(escapeRegExp(thousandsSep), "g") || ",";

    // a number can have the thousand separator multiple times. ex: 1,000,000.00
    value = value.replaceAll(thousandsSepRegex, "");
    // a number only have one decimal separator
    value = value.replace(new RegExp(escapeRegExp(decimalPoint), "g") || ".", ".");
    return Number(value);
}

/**
 * group 1: sign
 * group 2: the number to parse
 */
const POSSIBLE_NUMBER_REGEX = new RegExp("^([\\-+]*)([\\d\\.,\\s]*)$");

function lenientParseNumber(value, options) {
    const matchedValue = value.match(POSSIBLE_NUMBER_REGEX);
    const sign = matchedValue[1];
    value = matchedValue[2];

    if (sign.length > 1) {
        throw new Error("Invalid input. Can't have multiple signs.");
    }

    // Remove all whitespaces.
    value = value.replaceAll(/\s+/g, "");

    // Remove thousands separators and set decimal point as ".".
    const separators = value.replaceAll(/\d/g, "");
    if (separators.length === 1) {
        const [char] = separators;
        if (char === options.thousandsSep) {
            value = value.replace(char, "");
        } else {
            value = value.replace(char, ".");
        }
    } else if (separators.length === 2) {
        const [thousandsSep, decimalPoint] = [...separators];
        if (thousandsSep === decimalPoint) {
            // then no decimal point, all thousands sep
            value = value.replaceAll(thousandsSep, "");
        } else {
            value = value.replace(thousandsSep, "").replace(decimalPoint, ".");
        }
    } else if (separators.length > 2) {
        const [decimalPoint, ...thousandsSeps] = [...separators].reverse();
        // thousandsSeps should all be the same
        const [thousandsSep, invalid] = [...new Set(thousandsSeps)];
        if (invalid) {
            throw new Error("wrong sequence of thousands separators and decimal point");
        }
        if (thousandsSep === decimalPoint) {
            value = value.replaceAll(thousandsSep, "");
        } else {
            value = value.replaceAll(thousandsSep, "").replace(decimalPoint, ".");
        }
    }

    return Number(`${sign}${value}`);
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
    const thousandsSepRegex = localization.thousandsSep || "";
    const decimalPointRegex = localization.decimalPoint;
    return parseNumber(value, {
        thousandsSep: thousandsSepRegex,
        decimalPoint: decimalPointRegex,
    });
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
    const thousandsSepRegex = localization.thousandsSep || "";
    const decimalPointRegex = localization.decimalPoint;
    return parseNumber(value, {
        thousandsSep: thousandsSepRegex,
        decimalPoint: decimalPointRegex,
        truncate: true,
    });
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
 * This is a very lenient function such that it just strips non-numeric characters at the
 * beginning and end of the string, and then tries to parse the remaining string as a float.
 *
 * @param {string} value
 * @returns {number}
 */
export function parseMonetary(value) {
    value = value.trim();
    const regex = new RegExp(`^[^\\d\\-+=]*(?<strToParse>.*?)[^\\d]*$`);
    const match = value.match(regex);
    if (!match) {
        throw new InvalidNumberError(`"${value}" is not a valid number.`);
    }
    value = match.groups.strToParse;
    return parseFloat(value);
}

registry
    .category("parsers")
    .add("date", parseDate)
    .add("datetime", parseDateTime)
    .add("float", parseFloat)
    .add("float_time", parseFloatTime)
    .add("integer", parseInteger)
    .add("many2one_reference", parseInteger)
    .add("monetary", parseMonetary)
    .add("percentage", parsePercentage);
