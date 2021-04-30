/** @odoo-module alias=point_of_sale.utils **/

import { float_is_zero, round_precision } from 'web.utils';

function getFileAsText(file) {
    return new Promise((resolve, reject) => {
        if (!file) {
            reject();
        } else {
            const reader = new FileReader();
            reader.addEventListener('load', function () {
                resolve(reader.result);
            });
            reader.addEventListener('abort', reject);
            reader.addEventListener('error', reject);
            reader.readAsText(file);
        }
    });
}

/**
 * This global variable is used by nextFrame to store the timer and
 * be able to cancel it before another request for animation frame.
 */
let timer = null;

/**
 * Wait for the next animation frame to finish.
 */
const nextFrame = () => {
    return new Promise((resolve) => {
        cancelAnimationFrame(timer);
        timer = requestAnimationFrame(() => {
            resolve();
        });
    });
};

function isRpcError(error) {
    return !(error instanceof Error) && error.message && [100, 200, 404, -32098].includes(error.message.code);
}

/**
 * Simple implementation of deep clone. Doesn't take into account
 * Date fields.
 * @param {Object} obj
 */
function cloneDeep(obj, overrides = {}) {
    const newObj = obj instanceof Array ? [] : {};
    for (const key in obj) {
        if (obj[key] && typeof obj[key] == 'object') {
            newObj[key] = cloneDeep(obj[key]);
        } else {
            newObj[key] = obj[key];
        }
    }
    return Object.assign(newObj, overrides);
}

/**
 * Taken from uuidv4 of o_spreadsheet.js.
 */
function uuidv4() {
    if (window.crypto && window.crypto.getRandomValues) {
        //@ts-ignore
        return ([1e7] + -1e3 + -4e3 + -8e3 + -1e11).replace(/[018]/g, (c) =>
            (c ^ (crypto.getRandomValues(new Uint8Array(1))[0] & (15 >> (c / 4)))).toString(16)
        );
    } else {
        // mainly for jest and other browsers that do not have the crypto functionality
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
            var r = (Math.random() * 16) | 0,
                v = c == 'x' ? r : (r & 0x3) | 0x8;
            return v.toString(16);
        });
    }
}

function barcodeRepr(parsedCode) {
    if (parsedCode.code.length > 32) {
        return parsedCode.code.substring(0, 29) + '...';
    } else {
        return parsedCode.code;
    }
}

function sum(array, selector = (item) => item) {
    return array.reduce((total, item) => total + selector(item), 0);
}

/**
 * Returns the max of the given date strings.
 * @param {string[]} dateStrings
 */
function maxDateString(...dateStrings) {
    return dateStrings.reduce((max, item) => {
        if (max >= item) return max;
        return item;
    }, '');
}

function generateWrappedName(name) {
    var MAX_LENGTH = 24; // 40 * line ratio of .6
    var wrapped = [];
    var current_line = '';

    while (name.length > 0) {
        var space_index = name.indexOf(' ');

        if (space_index === -1) {
            space_index = name.length;
        }

        if (current_line.length + space_index > MAX_LENGTH) {
            if (current_line.length) {
                wrapped.push(current_line);
            }
            current_line = '';
        }

        current_line += name.slice(0, space_index + 1);
        name = name.slice(space_index + 1);
    }

    if (current_line.length) {
        wrapped.push(current_line);
    }

    return wrapped;
}

/**
 * Rounds the given value base on the given decimal precision. It considers the sign
 * different from how round_precision does it. This is important because we observed
 * a pattern in cash rounding such that the change of the order (the amount to be returned
 * to the customer) can be computed by rounding the amount remaining that is negative.
 * So, if the amount remaining is -0.51, and if rounding is necessary in the opened
 * session, the change is `-round(-0.51)` which is `0.50` if the rounding precision
 * is `0.05`.
 * E.g.
 * ```js
 *  roundPrec(10.02, 0.03, 'HALF-UP') -> 10.03
 *  roundPrec(10.01, 0.03, 'HALF-UP') -> 10
 *  roundPrec(10.01, 0.05, 'UP') -> 10.05
 *  roundPrec(10.04, 0.05, 'DOWN') -> 10.05
 *  roundPrec(10.04, 0.05, 'DOWN') -> 10
 *  // but the following should not round because exact multiple
 *  roundPrec(10.05, 0.05, 'HALF-UP') -> 10.05
 *  roundPrec(10.05, 0.05, 'UP') -> 10.05
 *  roundPrec(10.05, 0.05, 'DOWN') -> 10.05
 *  // and it considers the sign
 *  roundPrec(-10.01, 0.05, 'DOWN') -> -10.05 // snaps to a lower value
 *  roundPrec(-10.01, 0.05, 'UP') -> -10 // snaps to a higher value
 * ```
 * @tests test_posRound.js
 * @param {number} value
 * @param {number} prec
 * @param {'HALF-UP' | 'UP' | 'DOWN'} [method=HALF-UP]
 * @param {number} decimalPlaces used to identify if the value is a multiple of the prec
 * @return {number}
 */
function posRound(value, prec, method = 'HALF-UP', decimalPlaces) {
    const _isMultiple = (a, b) => {
        const remainder = a % b;
        if (float_is_zero(remainder, decimalPlaces)) {
            return true;
        } else {
            // since we are taking modulo of floats, it is possible that the remainder
            // is near the value of b which means it is still a multiple.
            // try in the console: 10.02 % 0.02 -> 0.019999999999999366
            return float_is_zero(remainder - b, decimalPlaces);
        }
    };
    if (_isMultiple(value, prec)) {
        return value;
    } else {
        // Calculation example:
        // Say rounder = Math.round
        // value = 10.03, prec = 0.02
        // quotient -> 10.03 / 0.02 = 501.49999999999994
        // enoughToBePreciseQuotient -> round_precision(501.49999999999994, epsilon) -> 501.5
        // roundedQuotient -> rounder(501.5) -> 502
        // result is 502 * 0.02 -> 10.040000000000001
        const epsilon = 1 / Math.pow(10, decimalPlaces);
        const rounder = { 'HALF-UP': Math.round, UP: Math.ceil, DOWN: Math.floor }[method];
        const quotient = value / prec;
        const enoughToBePreciseQuotient = round_precision(quotient, epsilon);
        const roundedQuotient = rounder(enoughToBePreciseQuotient);
        return roundedQuotient * prec;
    }
}

/**
 * /!\ ATTENTION: not the same to `float_compare` of orm.
 *
 * Compares a and b based on the given decimal digits.
 * @param {number} val1
 * @param {number} val2
 * @param {number?} decimalPlaces number of decimal digits
 * @return {-1 | 0 | 1} If a and b are equal, returns 0. If a greater than b, returns 1. Otherwise returns -1.
 */
function posFloatCompare(val1, val2, decimalPlaces) {
    const delta = val1 - val2;
    if (float_is_zero(delta, decimalPlaces)) return 0;
    return delta > 0 ? 1 : -1;
}

export default {
    getFileAsText,
    nextFrame,
    isRpcError,
    cloneDeep,
    uuidv4,
    barcodeRepr,
    sum,
    maxDateString,
    generateWrappedName,
    posRound,
    posFloatCompare,
};
