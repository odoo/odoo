import { parseDate, parseDateTime } from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";
import { evaluateExpr } from "@web/core/py_js/py";
import { registry } from "@web/core/registry";
import { escapeRegExp } from "@web/core/utils/strings";
import { ArithmeticOperation } from "@web/model/relational_model/operation";
import { durationUnitsRegex, normalizeTimeStr } from "@web/core/l10n/time";

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

// A number can use any of these interchangeably as its decimal separator,
// regardless of the locale's own configured one.
const DECIMAL_SEPARATORS = ".,٫";
const DECIMAL_SEPARATOR_REGEX = new RegExp(`.*([${DECIMAL_SEPARATORS}])[^${DECIMAL_SEPARATORS}]*`);
const SINGLE_NUMBER_REGEX = new RegExp(`^[\\d${DECIMAL_SEPARATORS}'-]+$`);

function evaluateMathematicalExpression(expr, context = {}) {
    let safeEvalString = "";
    for (let v of expr.replace(/\s+/g, "").split(/([-+*/()^])/)) {
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
 * @param {boolean} options.integer - if true, only integers are allowed
 * @returns {number}
 */
function parseNumber(value, options = {}) {
    value = value.trim();

    if (value === "") {
        return 0;
    }
    if (value.startsWith("=")) {
        value = evaluateMathematicalExpression(value.substring(1));
        if (options.truncate) {
            value = Math.trunc(value);
        }
        return Number(value);
    }

    if (!options.integer) {
        const dp = value.match(DECIMAL_SEPARATOR_REGEX)?.[1];

        if (dp) {
            const count = value.split(dp).length - 1;
            if (count === 1) {
                const cleanupRegex = new RegExp(`[^\\deE\\-${dp}]`, "g");
                value = value.replace(cleanupRegex, "");
                value = value.replace(dp, ".");
                return Number(value);
            }
        }
    }

    value = value.replace(/[^\deE-]/g, "");
    return Number(value);
}

// -----------------------------------------------------------------------------
// Exports
// -----------------------------------------------------------------------------

export class InvalidNumberError extends Error {}
export class DurationParseError extends Error {}

/**
 * Try to extract a float from a string.
 *
 * @param {string} value
 * @returns {number} a float
 */
export function parseFloat(value, { allowOperation = false } = {}) {
    const operation = allowOperation ? ArithmeticOperation.parse(value, parseFloat) : null;
    if (operation) {
        return operation;
    }
    const parsed = parseNumber(value);
    if (isNaN(parsed)) {
        throw new InvalidNumberError(`"${value}" is not a correct number`);
    }
    return parsed;
}

/**
 * Try to extract a float time from a string.
 * The float time can have two formats: float or integer:integer.
 *
 * @param {string} value
 * @param {UnitOfTime} [unit="hours"]
 * @returns {number} a float
 */
export function parseFloatTime(value, unit = "hours") {
    value = value.trim();
    let duration;
    if (value.startsWith("=")) {
        duration = { hours: 0, minutes: 0, seconds: 0 };
        duration[unit] = evaluateMathematicalExpression(value.substring(1));
    } else {
        duration = parseDuration(value, unit);
    }

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
 * @param {UnitOfTime} [unit="hours"]
 * @return {Duration}
 */
function parseDuration(value, unit = "hours") {
    let isNegative;
    const regexTimes = durationUnitsRegex();
    const duration = {
        hours: 0,
        minutes: 0,
        seconds: 0,
    };
    const originalValue = value;
    value = normalizeTimeStr(value, true);

    if (!value) {
        return duration;
    }

    if (value[0] === "-") {
        isNegative = true;
        value = value.substring(1);
    }

    value = value.replaceAll(" ", "");

    // Single number: only if the value contains no unit-label characters.
    // parseNumber strips noise aggressively, so "2小时30分钟45秒" → 23045 without this guard.
    const asNumber = SINGLE_NUMBER_REGEX.test(value) ? parseNumber(value) : NaN;
    if (!isNaN(asNumber)) {
        duration[unit] = asNumber;
    }

    // 12:30:45 format
    else if (value.match(/(\d+)?:\d*(:\d*)?/)) {
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
    }

    // 12h 30m 45s format
    else if (
        value.match(regexTimes.hours) ||
        value.match(regexTimes.minutes) ||
        value.match(regexTimes.seconds)
    ) {
        let temp;
        if ((temp = value.match(regexTimes.hours))) {
            duration.hours = parseInt(temp[1], 10);
            value = value.replace(regexTimes.hours, "");
        }
        if ((temp = value.match(regexTimes.minutes) || value.match(/^(\d+)$/))) {
            duration.minutes = parseInt(temp[1], 10);
            value = value.replace(/^\d+$/, "");
            value = value.replace(regexTimes.minutes, "");
        }
        if ((temp = value.match(regexTimes.seconds) || value.match(/^(\d+)$/))) {
            duration.seconds = parseInt(temp[1], 10);
        }
    } else {
        throw new DurationParseError(`Couldn't parse '${originalValue}'.`);
    }

    if (isNegative) {
        duration.hours = -duration.hours;
        duration.minutes = -duration.minutes;
        duration.seconds = -duration.seconds;
    }
    return duration;
}

/**
 * Try to extract an integer from a string.
 *
 * @param {string} value
 * @returns {number} an integer
 */
export function parseInteger(value, { allowOperation = false } = {}) {
    const operation = allowOperation ? ArithmeticOperation.parse(value, parseInteger) : null;
    if (operation) {
        return operation;
    }
    const parsed = parseNumber(value, {
        truncate: true,
        integer: true,
    });
    if (!Number.isInteger(parsed)) {
        throw new InvalidNumberError(`"${value}" is not a correct number`);
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
 *
 * @param {string} value
 * @returns {number} float
 */
export function parsePercentage(value) {
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
