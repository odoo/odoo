/** @odoo-module **/

import { localization as l10n } from "@web/core/l10n/localization";
import { _t } from "@web/core/l10n/translation";
import { intersperse } from "@web/core/utils/strings";

/**
 * @param {Number} value
 * @param {Number} comparisonValue
 * @returns {Number}
 */
export function computeVariation(value, comparisonValue) {
    if (isNaN(value) || isNaN(comparisonValue)) {
        return NaN;
    }
    if (comparisonValue === 0) {
        if (value === 0) {
            return 0;
        } else if (value > 0) {
            return 1;
        } else {
            return -1;
        }
    }
    return (value - comparisonValue) / Math.abs(comparisonValue);
}

/**
 * Returns value clamped to the inclusive range of min and max.
 *
 * @param {Number} num
 * @param {Number} min
 * @param {Number} max
 * @returns {Number}
 */
export function clamp(num, min, max) {
    return Math.max(Math.min(num, max), min);
}

/**
 * Inserts "thousands" separators in the provided number.
 *
 * @param {string} string representing integer number
 * @param {string} [thousandsSep=","] the separator to insert
 * @param {number[]} [grouping=[]]
 *   array of relative offsets at which to insert `thousandsSep`.
 *   See `strings.intersperse` method.
 * @returns {string}
 */
export function insertThousandsSep(number, thousandsSep = ",", grouping = []) {
    const negative = number[0] === "-";
    number = negative ? number.slice(1) : number;
    return (negative ? "-" : "") + intersperse(number, grouping, thousandsSep);
}

/**
 * Format a number to a human readable format. For example, 3000 could become 3k.
 * Or massive number can use the scientific exponential notation.
 *
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
export function humanNumber(number, options = { decimals: 0, minDigits: 1 }) {
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
