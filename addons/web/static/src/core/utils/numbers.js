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
