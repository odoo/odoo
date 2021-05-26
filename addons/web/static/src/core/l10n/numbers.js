/** @odoo-module **/

import { escapeRegExp, intersperse } from "../utils/strings";
import { localization } from "./localization";
import { _lt } from "./translation";

class InvalidNumberError extends Error {}

// -----------------------------------------------------------------------------
// Helpers
// -----------------------------------------------------------------------------

/**
 * Inserts "thousands" separators in the provided number.
 *
 * @param {number} [num] integer number
 * @param {string} [thousandsSep=","] the separator to insert
 * @param {number[]} [grouping=[3,0]]
 *   array of relative offsets at which to insert `thousandsSep`.
 *   See `strings.intersperse` method.
 * @returns {string}
 */
function insertThousandsSep(num, thousandsSep = ",", grouping = [3, 0]) {
    let numStr = `${num}`;
    const negative = numStr[0] === "-";
    numStr = negative ? numStr.slice(1) : numStr;
    return (negative ? "-" : "") + intersperse(numStr, grouping, thousandsSep);
}

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

/**
 * Formats a number into a more readable string representing a float.
 *
 * @param {number|false} value
 * @param {Object} options additional options
 * @param {number} [options.precision=2] number of digits to keep after decimal point
 * @param {string} [options.decimalPoint="."] decimal separating character
 * @param {string} [options.thousandsSep=""] thousands separator to insert
 * @param {number[]} [options.grouping]
 *   array of relative offsets at which to insert `thousandsSep`.
 *   See `numbers.insertThousandsSep` method.
 * @returns {string}
 */
export function formatFloat(value, options = {}) {
    if (value === false) {
        return "";
    }
    const grouping = options.grouping || localization.grouping;
    const thousandsSep = options.thousandsSep || localization.thousandsSep;
    const decimalPoint = options.decimalPoint || localization.decimalPoint;
    const formatted = value.toFixed(options.precision || 2).split(".");
    formatted[0] = insertThousandsSep(+formatted[0], thousandsSep, grouping);
    return formatted.join(decimalPoint);
}

/**
 * Try to extract a float from a string. The localization is considered in the process.
 *
 * @param {string} value
 * @returns {number} a float
 */
export function parseFloat(value) {
    let thousandsSepRegex = new RegExp(escapeRegExp(localization.thousandsSep), "g");
    let decimalPointRegex = new RegExp(escapeRegExp(localization.decimalPoint), "g");
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
    let thousandsSepRegex = new RegExp(escapeRegExp(localization.thousandsSep), "g");
    let decimalPointRegex = new RegExp(escapeRegExp(localization.decimalPoint), "g");
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
    let values = value.split("&nbsp;");
    if (values.length === 1) {
        return parseFloat(value);
    }
    let currency;
    if (options.currencyId) {
        currency = odoo.session_info.currencies[options.currencyId];
    } else {
        currency = Object.values(odoo.session_info.currencies)[0];
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
 * Format a number to a human readable format.
 * By example, 3000 could become 3k. Or massive number can use the scientific exponential notation.
 *
 * @param {number} number to format
 * @param {Object} [options] Options to format
 * @param {number} [options.decimals=0] maximum number of decimals to use
 * @param {number} [options.minDigits=1]
 *    the minimum number of digits to preserve when switching to another
 *    level of thousands (e.g. with a value of '2', 4321 will still be
 *    represented as 4321 otherwise it will be down to one digit (4k))
 * @returns {string}
 */
export function humanNumber(number, options = { decimals: 0, minDigits: 1 }) {
    number = Math.round(number);
    const decimals = options.decimals || 0;
    const minDigits = options.minDigits || 1;
    const d2 = Math.pow(10, decimals);
    const numberMagnitude = +number.toExponential().split("e+")[1];
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
    const { decimalPoint, grouping, thousandsSep } = localization;
    const [integerPart, decimalPart] = String(number).split(".");
    const int = insertThousandsSep(sign * Number(integerPart), thousandsSep, grouping);
    if (!decimalPart) {
        return int + symbol;
    }
    return int + decimalPoint + decimalPart + symbol;
}
