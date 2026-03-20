import { parseDate, parseDateTime } from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";
import { evaluateExpr } from "@web/core/py_js/py";
import { registry } from "@web/core/registry";
import { escapeRegExp } from "@web/core/utils/strings";
import { ArithmeticOperation } from "@web/model/relational_model/operation";
import { durationUnitsRegex, normalizeTimeStr } from "../../core/l10n/time";

/**
 * @typedef Duration
 * @property {number} hours
 * @property {number} minutes
 * @property {number} seconds
 *
 * @typedef {"hours"|"minutes"|"seconds"} UnitOfTime
 */

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
 * @returns {number}
 */
function parseNumber(value, options = {}) {
    if (value.startsWith("=")) {
        value = evaluateMathematicalExpression(value.substring(1));
        if (options.truncate) {
            value = Math.trunc(value);
        }
    } else {
        // A whitespace thousands separator is equivalent to any whitespace character.
        // E.g. "1  000 000" should be parsed as 1000000 even if the
        // thousands separator is nbsp.
        const thousandsSepRegex = options.thousandsSep.match(/\s+/)
            ? /\s+/g
            : new RegExp(escapeRegExp(options.thousandsSep), "g") || ",";

        // a number can have the thousand separator multiple times. ex: 1,000,000.00
        value = value.replaceAll(thousandsSepRegex, "");
        // a number only have one decimal separator
        value = value.replace(new RegExp(escapeRegExp(options.decimalPoint), "g") || ".", ".");
    }

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
export function parseFloat(value, { allowOperation = false } = {}) {
    const operation = allowOperation ? ArithmeticOperation.parse(value, parseFloat) : null;
    if (operation) {
        return operation;
    }
    const thousandsSepRegex = localization.thousandsSep || "";
    const decimalPointRegex = localization.decimalPoint;
    let parsed = parseNumber(value, {
        thousandsSep: thousandsSepRegex,
        decimalPoint: decimalPointRegex,
    });
    if (isNaN(parsed)) {
        parsed = parseNumber(value, {
            thousandsSep: ",",
            decimalPoint: ".",
        });
        if (isNaN(parsed)) {
            throw new InvalidNumberError(`"${value}" is not a correct number`);
        }
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
 *
 * Parse a string of a duration to float value based on unit
 * e.g.: 1h 30m in hours would be 1.5 
 * 
 * @param {string} value
 * @param {UnitOfTime} unit
 */
export function parseFloatDuration(value, unit) {
    const duration = parseDuration(value, unit);

    if (unit === "hours") {
        return duration.hours + duration.minutes / 60 + duration.seconds / 3600;
    } else if (unit === "minutes") {
        return duration.hours * 60 + duration.minutes + duration.seconds / 60;
    } else {
        return duration.hours * 3600 + duration.minutes * 60 + duration.seconds;
    }
}

/**
 *
 * Parse a string into object Duration. The string can take 3 formats.
 * - A single number that will be interpreted as the given unit.
 * - Numeric format as hh:mm:ss
 * - Human format as 12h 30m 45s (depends of the local)
 *
 * @param {string} value
 * @param {UnitOfTime} unit
 * @return {Duration}
 */
export function parseDuration(value, unit = "hours") {
    let isNegative;
    const duration = {
        hours: 0,
        minutes: 0,
        seconds: 0,
    };

    if (!value) {
        return duration;
    }

    if (value[0] === "-") {
        isNegative = true;
        value = value.substring(1);
    }

    value = value.replaceAll(" ", "");
    value = value
        .replaceAll(localization.decimalPoint, ".")
        .replaceAll(localization.thousandsSep, "");

    // Single number
    if (!isNaN(value)) {
        duration[unit] = Number(value);
        value = "";
    }

    // 12:30:45 format
    else if (value.match(/\d+:\d*(:\d*)?/)) {
        const result = value.split(":");
        let unitFound = result.length === 3;
        let i = 0;
        for (const key of Object.keys(duration)) {
            if (!unitFound && key === unit) {
                unitFound = true;
            }

            if (unitFound) {
                duration[key] = parseInt(result[i], 10) || 0;
                i++;
            }
        }
        value = "";
    }

    // 12h 30m 45s format
    else {
        const regexTimes = durationUnitsRegex();

        value = normalizeTimeStr(value, true);
        let temp;
        if ((temp = value.match(regexTimes.hours))) {
            duration.hours = parseInt(temp[1], 10);
            value = value.replace(regexTimes.hours, "");
        }
        if ((temp = value.match(regexTimes.minutes) || value.match(/^(\d+$)/))) {
            duration.minutes = parseInt(temp[1], 10);
            value = value.replace(/^\d+$/, "");
            value = value.replace(regexTimes.minutes, "");
        }
        if ((temp = value.match(regexTimes.seconds) || value.match(/^(\d+)$/))) {
            duration.seconds = parseInt(temp[1], 10);
        }
    }

    if (isNegative) {
        duration.hours = -duration.hours;
        duration.minutes = -duration.minutes;
        duration.seconds = -duration.seconds;
    }
    return duration;
}

/**
 * Try to extract an integer from a string. The localization is considered in the process.
 *
 * @param {string} value
 * @returns {number} an integer
 */
export function parseInteger(value, { allowOperation = false } = {}) {
    const operation = allowOperation ? ArithmeticOperation.parse(value, parseInteger) : null;
    if (operation) {
        return operation;
    }
    const thousandsSepRegex = localization.thousandsSep || "";
    const decimalPointRegex = localization.decimalPoint;
    let parsed = parseNumber(value, {
        thousandsSep: thousandsSepRegex,
        decimalPoint: decimalPointRegex,
        truncate: true,
    });
    if (!Number.isInteger(parsed)) {
        parsed = parseNumber(value, {
            thousandsSep: ",",
            decimalPoint: ".",
            truncate: true,
        });
        if (!Number.isInteger(parsed)) {
            throw new InvalidNumberError(`"${value}" is not a correct number`);
        }
    }
    if (parsed < -2147483648 || parsed > 2147483647) {
        throw new InvalidNumberError(
            `"${value}" is out of bounds (integers should be between -2,147,483,648 and 2,147,483,647)`
        );
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
 * This is a very lenient function such that it ignores everything before we encounter a substring consisting of either
 * - a sign (- or +)
 * - an equals sign (signaling the start of a mathematical expression)
 * - a decimal point
 * - a number
 * We then remove any non-numeric characters at the end
 *
 *
 * @param {string} value
 * @returns {number}
 */
export function parseMonetary(value, { allowOperation = false } = {}) {
    const operation = allowOperation ? ArithmeticOperation.parse(value, parseMonetary) : null;
    if (operation) {
        return operation;
    }
    value = value.trim();
    const startMatch = value.match(
        new RegExp(`[\\d\\-+=]|${escapeRegExp(localization.decimalPoint)}`)
    );
    if (startMatch) {
        value = value.substring(startMatch.index);
    }
    value = value.replace(/\D*$/, "");
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
