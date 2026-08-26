import { parseDate, parseDateTime } from "@web/core/l10n/dates";
import { evaluateExpr } from "@web/core/py_js/py";
import { registry } from "@web/core/registry";
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

function evaluateMathematicalExpression(expr, context = {}, parseTokenFn = parseFloat) {
    let safeEvalString = "";
    for (let v of expr.replace(/\s+/g, "").split(/([-+*/()^])/)) {
        if (!["+", "-", "*", "/", "(", ")", "^"].includes(v) && v.length) {
            // check if this is a float and take into account user delimiter preference
            v = parseTokenFn(v);
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

    let hasUnambiguousDecimalPoint = false;
    if (!options.integer) {
        const dp = value.match(DECIMAL_SEPARATOR_REGEX)?.[1];

        if (dp) {
            const count = value.split(dp).length - 1;
            if (count === 1) {
                const cleanupRegex = new RegExp(`[^\\deE\\-${dp}]`, "g");
                value = value.replace(cleanupRegex, "");
                value = value.replace(dp, ".");
                hasUnambiguousDecimalPoint = true;
            }
        }
    }
    if (!hasUnambiguousDecimalPoint) {
        value = value.replace(/[^\deE-]/g, "");
    }

    // A stray e/E isn't a real exponent marker unless flanked by a digit before and an
    // optionally-signed digit after (e.g. the E in "EUR"/"EUROS" gets removed).
    if (/[eE]/.test(value) && !/^-?(\d+(\.\d+)?|\.\d+)[eE]-?\d+$/.test(value)) {
        value = value.replace(/[eE]/g, "");
    }
    // A "-" is only meaningful as a leading sign or an exponent sign (right after e/E);
    // anywhere else it's noise (e.g. the trailing "-" in "50,-"). Checked positionally
    // instead of with a lookbehind assertion, unsupported in Safari < 16.4.
    value = value.replace(/-/g, (match, offset) => {
        const isLeadingSign = offset === 0;
        const isExponentSign = offset > 0 && /[eE]/.test(value[offset - 1]);
        return isLeadingSign || isExponentSign ? match : "";
    });

    if (value === "") {
        return NaN;
    }
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
    if (isNaN(parsed) || !isFinite(parsed)) {
        throw new InvalidNumberError(`"${value}" is not a correct number`);
    }
    return parsed;
}

/**
 * Try to extract a float time from a string.
 * The float time can have two formats: float or integer:integer.
 *
 * It also supports duration formulas, e.g. "=1h+30m-15m*2" to set an absolute
 * value, or "+=30m" / "-=1h+15m" to increment/decrement the current value of
 * the field.
 *
 * @param {string} value
 * @param {UnitOfTime} [unit="hours"]
 * @returns {number|import("@web/model/relational_model/operation").Operation} a float or an Operation
 */
export function parseFloatTime(value, unit = "hours") {
    // Tolerate a trailing operator (e.g. "1h+"): the user is still typing.
    const evaluateDurationFormula = (expr) =>
        evaluateMathematicalExpression(expr.replace(/[-+*/]\s*$/, ""), {}, (v) =>
            parseFloatTime(v, unit)
        );

    value = value.trim();
    const operation = ArithmeticOperation.parse(value, evaluateDurationFormula);
    if (operation) {
        return operation;
    }

    if (value.startsWith("=")) {
        return evaluateDurationFormula(value.substring(1));
    }
    let duration = parseDuration(value, unit);

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

    if (value[0] === "-") {
        isNegative = true;
        value = value.substring(1);
    }

    if (!value) {
        return duration;
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

registry
    .category("parsers")
    .add("date", parseDate)
    .add("datetime", parseDateTime)
    .add("float", parseFloat)
    .add("float_time", parseFloatTime)
    .add("integer", parseInteger)
    .add("many2one_reference", parseInteger)
    .add("monetary", parseFloat)
    .add("percentage", parsePercentage);
