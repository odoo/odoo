// @ts-check

/** @module @web/search/utils/group_by - Group-by descriptor parser and interval validation for search queries */

import { BACKEND_INTERVAL_OPTIONS, DEFAULT_INTERVAL } from "./dates";

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
    let spec;
    let [fieldName, interval] = descr.split(":");
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
            } else if (!(interval in BACKEND_INTERVAL_OPTIONS)) {
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
            if (!(interval in BACKEND_INTERVAL_OPTIONS)) {
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
