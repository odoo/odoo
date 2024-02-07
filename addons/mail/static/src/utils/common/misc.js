/* @odoo-module */

import { reactive } from "@odoo/owl";
import { Deferred } from "@web/core/utils/concurrency";

export function assignDefined(obj, data, keys = Object.keys(data)) {
    for (const key of keys) {
        if (data[key] !== undefined) {
            obj[key] = data[key];
        }
    }
    return obj;
}

export function assignIn(obj, data, keys = Object.keys(data)) {
    for (const key of keys) {
        if (key in data) {
            obj[key] = data[key];
        }
    }
    return obj;
}

// todo: move this some other place in the future
export function isDragSourceExternalFile(dataTransfer) {
    const dragDataType = dataTransfer.types;
    if (dragDataType.constructor === window.DOMStringList) {
        return dragDataType.contains("Files");
    }
    if (dragDataType.constructor === Array) {
        return dragDataType.includes("Files");
    }
    return false;
}

/**
 * @param {Object} target
 * @param {string|string[]} key
 * @param {Function} callback
 */
export function onChange(target, key, callback) {
    let proxy;
    function _observe() {
        // access proxy[key] only once to avoid triggering reactive get() many times
        const val = proxy[key];
        if (typeof val === "object" && val !== null) {
            void Object.keys(val);
        }
        if (Array.isArray(val)) {
            void val.length;
            void val.forEach((i) => i);
        }
    }
    if (Array.isArray(key)) {
        for (const k of key) {
            onChange(target, k, callback);
        }
        return;
    }
    proxy = reactive(target, () => {
        _observe();
        callback();
    });
    _observe();
    return proxy;
}

/**
 * @param {MediaStream} [stream]
 */
export function closeStream(stream) {
    stream?.getTracks?.().forEach((track) => track.stop());
}

/**
 * Compare two Luxon datetime.
 *
 * @param {import("@web/core/l10n/dates").NullableDateTime} date1
 * @param {import("@web/core/l10n/dates").NullableDateTime} date2
 * @returns {number} Negative if date1 is less than date2, positive if date1 is
 *  greater than date2, and 0 if they are equal.
 */
export function compareDatetime(date1, date2) {
    if (date1?.ts === date2?.ts) {
        return 0;
    }
    if (!date1) {
        return -1;
    }
    if (!date2) {
        return 1;
    }
    return date1.ts - date2.ts;
}

/**
 * Create a cacheable version of the `store.fetchData` The result of the request
 * is cached once acquired. In case of failure, the deferred is rejected and the
 * cache is reset allowing to retry the request when calling the function again.
 *
 * @param {import("@mail/core/common/store_service").Store} store
 * @param {string} key
 * @returns {() => import("@web/core/utils/concurrency").Deferred}
 */
export function makeCachedFetchData(store, key) {
    /**
     * @type {{ status: "not_fetched"|"fetching"|"fetched", deferred: import("@web/core/utils/concurrency").Deferred?}}
     */
    const state = { status: "not_fetched", deferred: null };
    return () => {
        if (["fetching", "fetched"].includes(state.status)) {
            return state.deferred;
        }
        state.status = "fetching";
        state.deferred = new Deferred();
        store.fetchData({ [key]: true }).then(
            (result) => {
                state.status = "fetched";
                state.deferred.resolve(result);
            },
            (error) => {
                state.status = "not_fetched";
                state.deferred.reject(error);
            }
        );
        return state.deferred;
    };
}
