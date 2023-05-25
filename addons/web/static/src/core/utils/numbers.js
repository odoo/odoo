/** @odoo-module **/

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
 * performs a half up rounding with arbitrary precision, correcting for float loss of precision
 * See the corresponding float_round() in server/tools/float_utils.py for more info
 *
 * @param {number} value the value to be rounded
 * @param {number} precision a precision parameter. eg: 0.01 rounds to two digits.
 */
export function roundPrecision(value, precision) {
    if (!value) {
        return 0;
    } else if (!precision || precision < 0) {
        precision = 1;
    }
    let normalizedValue = value / precision;
    const epsilon = Number.EPSILON * Math.abs(normalizedValue);
    // instead of this `epsilon` trick, we could use `Number.EPSILON` directly, but it
    // would not always give the desired outcome:
    // ex: if value == 10.45 * 123.5 => value == 1290.5749999999998,
    // but this value clearly represents the number 1290.575,
    // so it should be rounded to 1290.58, not 1290.57
    normalizedValue += Math.sign(normalizedValue) * epsilon;
    /**
     * Javascript performs strictly the round half up method, which is asymmetric. However, in
     * Python, the method is symmetric. For example:
     * - In JS, Math.round(-0.5) is equal to -0.
     * - In Python, round(-0.5) is equal to -1.
     * We want to keep the Python behavior for consistency.
     */
    // if precision is less than 1, it will be, in our use cases, a number that evenly divides 1,
    // (ex: 0.1, 0.00001, 0.25, 0.5)
    // This means that we expect 1/precision to be a whole number. We still round it though,
    // because we could run into problems for certain values of precision.
    // ex: 1/0.00001 -> 99999.99999999999
    const precisionMagnitude = precision < 1 ? Math.round(1 / precision) : 1 / precision;
    const roundedValue = Math.sign(normalizedValue) * Math.round(Math.abs(normalizedValue));
    return roundedValue / precisionMagnitude;
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
    return roundDecimals(value, decimals) === 0;
}
