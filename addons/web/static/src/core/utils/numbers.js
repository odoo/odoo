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
 * @param {number} min default 0
 * @param {number} max
 * @param {number} step default 1
 * @returns {number[]}
 */
export function range(start, stop, step = 1) {
    const array = [];
    for (let i = start; i < stop; i += step) {
        array.push(i);
    }
    return array;
}
