import { DEFAULT_INTERVAL, BACKEND_INTERVAL_OPTIONS } from "./dates";

/**
 * @param {string} descr
 */
function errorMsg(descr) {
    return `Invalid groupBy description: ${descr}`;
}

/**
 * @param {string} descr
 * @param {Object} fields
 * @returns {Object}
 */
export function getGroupBy(descr, fields) {
    let fieldName;
    let interval;
    let spec;
    [fieldName, interval] = descr.split(":");
    if (!fieldName) {
        throw Error();
    }
    if (fields) {
        if (!fields[fieldName] && !fieldName.includes(".")) {
            throw Error(errorMsg(descr));
        }
        const fieldType = fields[fieldName]?.type;
        if (["date", "datetime"].includes(fieldType)) {
            if (!interval) {
                interval = DEFAULT_INTERVAL;
            } else if (!Object.keys(BACKEND_INTERVAL_OPTIONS).includes(interval)) {
                throw Error(errorMsg(descr));
            }
            spec = `${fieldName}:${interval}`;
        } else if (interval) {
            throw Error(errorMsg(descr));
        } else {
            spec = fieldName;
            interval = null;
        }
    } else {
        if (interval) {
            if (!Object.keys(BACKEND_INTERVAL_OPTIONS).includes(interval)) {
                throw Error(errorMsg(descr));
            }
            spec = `${fieldName}:${interval}`;
        } else {
            spec = fieldName;
            interval = null;
        }
    }
    return {
        fieldName,
        interval,
        spec,
        toJSON() {
            return spec;
        },
    };
}
