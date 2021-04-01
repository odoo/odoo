/** @odoo-module **/

import { escapeRegExp, intersperse, sprintf } from "./strings";
import { localization } from "../localization/localization_settings";
import { _lt } from "../localization/translation";

/**
 * Formats a number into a string representing a float.
 *
 * @param {number|false} value
 * @param {Object} options additional options
 * @param {number} [options.precision=2] number of digits to keep after decimal point
 * @param {string} [options.decimalPoint="."] decimal separating character
 * @param {string} [options.thousandsSep=""] thousands separator to insert
 * @param {number[]} [options.grouping]
 *   array of relative offsets at which to insert `thousandsSep`.
 *   See `numbers.insertThousandsSep` method.
 * @returns string
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
 * Inserts "thousands" separators in the provided number.
 *
 * @param {number} [num] integer number
 * @param {string} [thousandsSep=","] the separator to insert
 * @param {number[]} [grouping=[3,0]]
 *   array of relative offsets at which to insert `thousandsSep`.
 *   See `strings.intersperse` method.
 * @returns {string}
 */
export function insertThousandsSep(num, thousandsSep = ",", grouping = [3, 0]) {
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
 * @returns number
 */
export function parseNumber(value, options = {}) {
  value = value.replace(options.thousandsSep || ",", "");
  value = value.replace(options.decimalPoint || ".", ".");
  return Number(value);
}

export function parseFloat(value) {
  let thousandsSepRegex = new RegExp(escapeRegExp(localization.thousandsSep), "g");
  let decimalPointRegex = new RegExp(escapeRegExp(localization.decimalPoint), "g");
  const parsed = parseNumber(value, {
    thousandsSep: thousandsSepRegex,
    decimalPoint: decimalPointRegex,
  });
  if (isNaN(parsed)) {
    throw new Error(sprintf(_lt("'%s' is not a correct float").toString(), value));
  }
  return parsed;
}

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
  number = sign * number;
  const { thousandsSep, grouping } = localization;
  return insertThousandsSep(number, thousandsSep, grouping) + symbol;
}
