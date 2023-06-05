/** @odoo-module */

import { reactive } from "@odoo/owl";

/**
 * Creates a side-effect that runs based on the content of reactive objects.
 *
 * @template {object[]} T
 * @param {(...args: [...T]) => void} cb callback for the effect
 * @param {[...T]} deps the reactive objects that the effect depends on
 */
export function effect(cb, deps) {
    const reactiveDeps = reactive(deps, () => {
        cb(...reactiveDeps);
    });
    cb(...reactiveDeps);
}

/**
 * Adds computed properties to a reactive object derived from multiples sources.
 *
 * @template {object} T
 * @template {object[]} U
 * @template {{[key: string]: (this: T, ...rest: [...U]) => unknown}} V
 * @param {T} obj the reactive object on which to add the computed
 * properties
 * @param {[...U]} sources the reactive objects which are needed to compute
 * the properties
 * @param {V} descriptor the object containing methods to compute the
 * properties
 * @returns {T & {[key in keyof V]: ReturnType<V[key]>}}
 */
export function withComputedProperties(obj, sources, descriptor) {
    for (const [key, compute] of Object.entries(descriptor)) {
        effect(
            (obj, sources) => {
                obj[key] = compute.call(obj, ...sources);
            },
            [obj, sources]
        );
    }
    return obj;
}

export class Reactive {
    constructor() {
        return reactive(this);
    }
}

/**
 * Creates a batched version of a callback so that all calls to it in the same
 * microtick will only call the original callback once.
 *
 * @param callback the callback to batch
 * @returns a batched version of the original callback
 */
export function batched(callback) {
    let called = false;
    return async (...args) => {
        // This await blocks all calls to the callback here, then releases them sequentially
        // in the next microtick. This line decides the granularity of the batch.
        await Promise.resolve();
        if (!called) {
            called = true;
            // so that only the first call to the batched function calls the original callback.
            // Schedule this before calling the callback so that calls to the batched function
            // within the callback will proceed only after resetting called to false, and have
            // a chance to execute the callback again
            Promise.resolve().then(() => (called = false));
            callback(...args);
        }
    };
}

/*
 * comes from o_spreadsheet.js
 * https://stackoverflow.com/questions/105034/create-guid-uuid-in-javascript
 * */
export function uuidv4() {
    // mainly for jest and other browsers that do not have the crypto functionality
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
        const r = (Math.random() * 16) | 0,
            v = c == "x" ? r : (r & 0x3) | 0x8;
        return v.toString(16);
    });
}

/**
 * Formats the given `url` with correct protocol and port.
 * Useful for communicating to local iot box instance.
 * @param {string} url
 * @returns {string}
 */
export function deduceUrl(url) {
    const { protocol } = window.location;
    if (!url.includes("//")) {
        url = `${protocol}//${url}`;
    }
    if (url.indexOf(":", 6) < 0) {
        url += ":" + (protocol === "https:" ? 443 : 8069);
    }
    return url;
}
