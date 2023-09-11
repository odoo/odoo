/** @odoo-module */

import { serializeDate } from "@web/core/l10n/dates";

const { DateTime } = luxon;

/**
 * Get the intersection of two arrays
 *
 * @param {Array} a
 * @param {Array} b
 *
 * @private
 * @returns {Array} intersection between a and b
 */
export function intersect(a, b) {
    return a.filter((x) => b.includes(x));
}

/**
 * Given an object of form {"1": {...}, "2": {...}, ...} get the maximum ID used
 * in this object
 * If the object has no keys, return 0
 *
 * @param {Object} o an object for which the keys are an ID
 *
 * @returns {number}
 */
export function getMaxObjectId(o) {
    const keys = Object.keys(o);
    if (!keys.length) {
        return 0;
    }
    const nums = keys.map((id) => parseInt(id, 10));
    const max = Math.max(...nums);
    return max;
}

/**
 * Convert a spreadsheet date representation to an odoo
 * server formatted date
 *
 * @param {Date} value
 * @returns {string}
 */
export function toServerDateString(value) {
    const date = DateTime.fromJSDate(value);
    return serializeDate(date);
}

/**
 * @param {number[]} array
 * @returns {number}
 */
export function sum(array) {
    return array.reduce((acc, n) => acc + n, 0);
}

function camelToSnakeKey(word) {
    const result = word.replace(/(.){1}([A-Z])/g, "$1 $2");
    return result.split(" ").join("_").toLowerCase();
}

/**
 * Recursively convert camel case object keys to snake case keys
 * @param {object} obj
 * @returns {object}
 */
export function camelToSnakeObject(obj) {
    const result = {};
    for (const [key, value] of Object.entries(obj)) {
        const isPojo = typeof value === "object" && value !== null && value.constructor === Object;
        result[camelToSnakeKey(key)] = isPojo ? camelToSnakeObject(value) : value;
    }
    return result;
}

/**
 * Check if the argument is falsy or is an empty object/array
 *
 * TODO : remove this and replace it by the one in o_spreadsheet xlsx import when its merged
 */
export function isEmpty(item) {
    if (!item) {
        return true;
    }
    if (typeof item === "object") {
        if (
            Object.values(item).length === 0 ||
            Object.values(item).every((val) => val === undefined)
        ) {
            return true;
        }
    }
    return false;
}

export function containsReferences(cell) {
    if (!cell.isFormula) {
        return false;
    }
    return cell.compiledFormula.tokens.some((token) => token.type === "REFERENCE");
}
