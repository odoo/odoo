/** @odoo-module alias=point_of_sale.utils **/

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
};
