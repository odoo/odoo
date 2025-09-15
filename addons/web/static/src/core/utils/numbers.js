import { localization as l10n } from "@web/core/l10n/localization";
import { _t } from "@web/core/l10n/translation";
import { intersperse } from "@web/core/utils/strings";

/**
 * Returns value clamped to the inclusive range of min and max.
 *
 * @param {number} num
 * @param {number} min
 * @param {number} max
 * @returns {number}
 */
export function clamp(num, min, max) {
    return Math.max(Math.min(num, max), min);
}

/**
 * A function to create flexibly-numbered lists of integers, handy for each and map loops.
 * step defaults to 1.
 * Returns a list of integers from start (inclusive) to stop (exclusive), incremented (or decremented) by step.
 * @param {number} start default 0
 * @param {number} stop
 * @param {number} step default 1
 * @returns {number[]}
 */
export function range(start, stop, step = 1) {
    const array = [];
    const nsteps = Math.floor((stop - start) / step);
    for (let i = 0; i < nsteps; i++) {
        array.push(start + step * i);
    }
    return array;
}

/**
 * Returns `value` rounded with `precision`, minimizing IEEE-754 floating point
 * representation errors, and applying the tie-breaking rule selected with
 * `method`, by default "HALF-UP" (away from zero).
 *
 * @param {number} value the value to be rounded
 * @param {number} precision a precision parameter. eg: 0.01 rounds to two digits.
 * @param {"HALF-UP" | "HALF-DOWN" | "HALF-EVEN" | "UP" | "DOWN"} [method="HALF-UP"] the rounding method used:
 *    - "HALF-UP" rounds to the closest number with ties going away from zero.
 *    - "HALF-DOWN" rounds to the closest number with ties going towards zero.
 *    - "HALF-EVEN" rounds to the closest number with ties going to the closest even number.
 *    - "UP" always rounds away from 0.
 *    - "DOWN" always rounds towards 0.
 */
export function roundPrecision(value, precision, method = "HALF-UP") {
    if (!value) {
        return 0;
    } else if (!precision || precision < 0) {
        precision = 1;
    }
    let roundingFactor = precision;
    let normalize = (val) => val / roundingFactor;
    let denormalize = (val) => val * roundingFactor;
    // inverting small rounding factors reduces rounding errors
    if (roundingFactor < 1) {
        roundingFactor = invertFloat(roundingFactor);
        [normalize, denormalize] = [denormalize, normalize];
    }
    const normalizedValue = normalize(value);
    const sign = Math.sign(normalizedValue);
    const epsilonMagnitude = Math.log2(Math.abs(normalizedValue));
    const epsilon = Math.pow(2, epsilonMagnitude - 50);
    let roundedValue;

    switch (method) {
        case "DOWN": {
            roundedValue = Math.trunc(normalizedValue + sign * epsilon);
            break;
        }
        case "HALF-DOWN": {
            roundedValue = Math.round(normalizedValue - sign * epsilon);
            break;
        }
        case "HALF-UP": {
            roundedValue = Math.round(normalizedValue + sign * epsilon);
            break;
        }
        case "HALF-EVEN": {
            const integral = Math.floor(normalizedValue);
            const remainder = Math.abs(normalizedValue - integral);
            const isHalf = Math.abs(0.5 - remainder) < epsilon;
            roundedValue = isHalf ? integral + (integral & 1) : Math.round(normalizedValue);
            break;
        }
        case "UP": {
            roundedValue = Math.trunc(normalizedValue + sign * (1 - epsilon));
            break;
        }
        default: {
            throw new Error(`Unknown rounding method: ${method}`);
        }
    }

    return denormalize(roundedValue);
}

export function roundDecimals(value, decimals) {
    /**
     * The following decimals introduce numerical errors:
     * Math.pow(10, -4) = 0.00009999999999999999
     * Math.pow(10, -5) = 0.000009999999999999999
     *
     * Such errors will propagate in roundPrecision and lead to inconsistencies between Python
     * and JavaScript. To avoid this, we parse the scientific notation.
     */
    return roundPrecision(value, parseFloat("1e" + -decimals));
}

/**
 * @param {number} value
 * @param {integer} decimals
 * @returns {boolean}
 */
export function floatIsZero(value, decimals) {
    return value === 0 || roundDecimals(value, decimals) === 0;
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

/**
 * Returns a string representing a float.  The result takes into account the
 * user settings (to display the correct decimal separator).
 *
 * @param {number} value the value that should be formatted
 * @param {Object} [options]
 * @param {number[]} [options.digits] the number of digits that should be used,
 *   instead of the default digits precision in the field.
 * @param {boolean} [options.humanReadable] if true, large numbers are formatted
 *   to a human readable format.
 * @param {string} [options.decimalPoint] decimal separating character
 * @param {string} [options.thousandsSep] thousands separator to insert
 * @param {number[]} [options.grouping] array of relative offsets at which to
 *   insert `thousandsSep`. See `insertThousandsSep` method.
 * @param {number} [options.decimals] used for humanNumber formmatter
 * @param {boolean} [options.trailingZeros=true] if false, the decimal part
 *   won't contain unnecessary trailing zeros.
 * @returns {string}
 */
export function formatFloat(value, options = {}) {
    let precision;
    if (options.digits && options.digits[1] !== undefined) {
        precision = options.digits[1];
    } else {
        precision = 2;
    }
    if (floatIsZero(value, precision)) {
        value = 0.0;
    }
    if (options.humanReadable) {
        return humanNumber(value, options);
    }
    const grouping = options.grouping || l10n.grouping;
    const thousandsSep = "thousandsSep" in options ? options.thousandsSep : l10n.thousandsSep;
    const decimalPoint = "decimalPoint" in options ? options.decimalPoint : l10n.decimalPoint;
    const formatted = value.toFixed(precision).split(".");
    formatted[0] = insertThousandsSep(formatted[0], thousandsSep, grouping);
    if (options.trailingZeros === false && formatted[1]) {
        formatted[1] = formatted[1].replace(/0+$/, "");
    }
    return formatted[1] ? formatted.join(decimalPoint) : formatted[0];
}

const _INVERTDICT = Object.freeze({
    1e-1: 1e+1, 1e-2: 1e+2, 1e-3: 1e+3, 1e-4: 1e+4, 1e-5: 1e+5,
    1e-6: 1e+6, 1e-7: 1e+7, 1e-8: 1e+8, 1e-9: 1e+9, 1e-10: 1e+10,
    2e-1: 5e+0, 2e-2: 5e+1, 2e-3: 5e+2, 2e-4: 5e+3, 2e-5: 5e+4,
    2e-6: 5e+5, 2e-7: 5e+6, 2e-8: 5e+7, 2e-9: 5e+8, 2e-10: 5e+9,
    5e-1: 2e+0, 5e-2: 2e+1, 5e-3: 2e+2, 5e-4: 2e+3, 5e-5: 2e+4,
    5e-6: 2e+5, 5e-7: 2e+6, 5e-8: 2e+7, 5e-9: 2e+8, 5e-10: 2e+9,
});

/**
 * Invert a number with increased accuracy.
 *
 * @param {number} value
 * @returns {number}
 */
export function invertFloat(value) {
    let res = _INVERTDICT[value];
    if (res === undefined) {
        const [coeff, expt] = value.toExponential().split("e").map(Number.parseFloat);
        res = Number.parseFloat(`${coeff}e${-expt}`) / Math.pow(coeff, 2);
    }
    return res;
}
