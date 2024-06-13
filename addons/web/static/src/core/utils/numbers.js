/** @odoo-module **/

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
    const epsilonMagnitude = Math.log2(Math.abs(normalizedValue));
    const epsilon = Math.pow(2, epsilonMagnitude - 52);
    normalizedValue += normalizedValue >= 0 ? epsilon : -epsilon;

    /**
     * Javascript performs strictly the round half up method, which is asymmetric. However, in
     * Python, the method is symmetric. For example:
     * - In JS, Math.round(-0.5) is equal to -0.
     * - In Python, round(-0.5) is equal to -1.
     * We want to keep the Python behavior for consistency.
     */
    const sign = normalizedValue < 0 ? -1.0 : 1.0;
    const roundedValue = sign * Math.round(Math.abs(normalizedValue));
    return roundedValue * precision;
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
