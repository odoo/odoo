/* @odoo-module */

import { reactive } from "@odoo/owl";

export function createLocalId(...args) {
    return args.join(",");
}

export function nullifyClearCommands(data) {
    for (const key in data) {
        if (!Array.isArray(data[key])) {
            continue;
        }
        data[key] = data[key].filter((val) => val[0] !== "clear");
        if (data[key].length === 0) {
            data[key] = null;
        }
    }
}

export function assignDefined(obj, data, keys = Object.keys(data)) {
    for (const key of keys) {
        if (data[key] !== undefined) {
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

const eventHandledWeakMap = new WeakMap();

/**
 * Returns whether the given event has been handled with the given markName.
 *
 * @param {Event} ev
 * @param {string} markName
 * @returns {boolean}
 */
export function isEventHandled(ev, markName) {
    if (!eventHandledWeakMap.get(ev)) {
        return false;
    }
    return eventHandledWeakMap.get(ev).includes(markName);
}

/**
 * Marks the given event as handled by the given markName. Useful to allow
 * handlers in the propagation chain to make a decision based on what has
 * already been done.
 *
 * @param {Event} ev
 * @param {string} markName
 */
export function markEventHandled(ev, markName) {
    if (!eventHandledWeakMap.get(ev)) {
        eventHandledWeakMap.set(ev, []);
    }
    eventHandledWeakMap.get(ev).push(markName);
}

/**
 * @param {Object} target
 * @param {string} key
 * @param {Function} callback
 */
export function onChange(target, key, callback) {
    const proxy = reactive(target, () => {
        void proxy[key];
        if (proxy[key] instanceof Object) {
            void Object.keys(proxy[key]);
        }
        callback();
    });
    void proxy[key];
    if (proxy[key] instanceof Object) {
        void Object.keys(proxy[key]);
    }
    return proxy;
}

/**
 * @param {MediaStream} [stream]
 */
export function closeStream(stream) {
    stream?.getTracks?.().forEach((track) => track.stop());
}
