/** @odoo-module **/

const ERROR = Symbol("error");

/**
 * @typedef {{ [typeof ERROR]: Error }} Err
 */

/**
 * @returns {Err}
 */
export function error() {
    return { [ERROR]: new Error(...arguments) };
}

export function isError(value) {
    return value !== null && typeof value === "object" && ERROR in value;
}

/**
 * @param {Err} error
 */
export function throwError(error) {
    throw error[ERROR];
}

export function bind(fn) {
    return (val) => (isError(val) ? val : fn(val));
}

export function compose(...fns) {
    return (val) => {
        for (let i = fns.length - 1; i >= 0; i--) {
            if (isError(val)) {
                return val;
            }
            val = fns[i](val);
        }
        return val;
    };
}

export function map(fn) {
    return (array) => {
        const result = [];
        const fnBinded = bind(fn);
        for (const a of array) {
            const val = fnBinded(a);
            if (isError(val)) {
                return val;
            }
            result.push(val);
        }
        return result;
    };
}

export function mapObject(fn) {
    return (object) => {
        const result = {};
        const fnBinded = bind(fn);
        for (const k in object) {
            const val = fnBinded(object[k]);
            if (isError(val)) {
                return val;
            }
            result[k] = val;
        }
        return result;
    };
}
