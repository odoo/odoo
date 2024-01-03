/** @odoo-module */

import { onWillRender, reactive, useState } from "@odoo/owl";
import { isIterable } from "@web/../lib/hoot-dom/hoot_dom_utils";
import { isNil } from "../hoot_utils";
import { CONFIG_KEYS, CONFIG_SCHEMA, FILTER_KEYS, FILTER_SCHEMA } from "./config";

/**
 * @typedef {typeof import("./config").DEFAULT_CONFIG} DEFAULT_CONFIG
 *
 * @typedef {typeof import("./config").DEFAULT_FILTERS} DEFAULT_FILTERS
 */

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const { Object, Set, URIError, URL, URLSearchParams, history, location } = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

const processParams = () => {
    const url = createURL({});
    url.search = "";
    for (const [key, value] of Object.entries(urlParams)) {
        if (isIterable(value)) {
            for (const value of urlParams[key]) {
                if (value) {
                    url.searchParams.append(key, value);
                }
            }
        } else if (value) {
            url.searchParams.set(key, String(value));
        }
    }
    return url;
};

const processURL = () => {
    const searchParams = new URLSearchParams(location.search);
    const searchKeys = new Set(searchParams.keys());
    for (const [configKey, { aliases, parse }] of Object.entries({
        ...CONFIG_SCHEMA,
        ...FILTER_SCHEMA,
    })) {
        const configKeys = [configKey, ...(aliases || [])];
        /** @type {string[]} */
        const values = [];
        let hasKey = false;
        for (const key of configKeys) {
            if (searchKeys.has(key)) {
                hasKey = true;
                values.push(...searchParams.getAll(key).filter(Boolean));
            }
        }
        if (hasKey) {
            urlParams[configKey] = parse(values);
        } else {
            delete urlParams[configKey];
        }
    }
};

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * @param {Partial<DEFAULT_CONFIG & DEFAULT_FILTERS>} params
 */
export function createURL(params) {
    const url = new URL(location.href);
    for (const key in params) {
        url.searchParams.delete(key);
        if (!CONFIG_KEYS.includes(key) && !FILTER_KEYS.includes(key)) {
            throw new URIError(`unknown URL param key: "${key}"`);
        }
        if (isIterable(params[key])) {
            for (const value of params[key]) {
                url.searchParams.append(key, value);
            }
        } else if (!isNil(params[key])) {
            url.searchParams.set(key, params[key]);
        }
    }
    return url;
}

/**
 * @param {string | URL} url
 * @param {string | URL} url
 */
export function goto(url, silent = false) {
    url = url.toString();
    history.replaceState({ path: url }, "", url);
    if (!silent) {
        processURL();
    }
}

export function refresh() {
    history.go();
}

/**
 * @param {Partial<DEFAULT_CONFIG & DEFAULT_FILTERS>} params
 */
export function setParams(params) {
    for (const [key, value] of Object.entries(params)) {
        if (!CONFIG_KEYS.includes(key) && !FILTER_KEYS.includes(key)) {
            throw new URIError(`unknown URL param key: "${key}"`);
        }
        if (value) {
            urlParams[key] = isIterable(value) ? [...value] : value;
        } else {
            delete urlParams[key];
        }
    }

    goto(processParams(), true);
}

/**
 * @param {...(keyof DEFAULT_CONFIG | keyof DEFAULT_FILTERS | "*")} keys
 */
export function subscribeToURLParams(...keys) {
    const state = useState(urlParams);
    if (keys.length) {
        const observedKeys = keys.includes("*") ? [...CONFIG_KEYS, ...FILTER_KEYS] : keys;
        onWillRender(() => observedKeys.forEach((key) => state[key]));
    }
    return state;
}

/**
 * @param {keyof DEFAULT_FILTERS} type
 * @param {string} id
 * @param {{
 *  debug?: boolean;
 *  ignore?: boolean;
 * }} [options]
 */
export function withParams(type, id, options) {
    const clearAll = () => Object.keys(nextParams).forEach((key) => nextParams[key].clear());

    const nextParams = Object.fromEntries(FILTER_KEYS.map((k) => [k, new Set(urlParams[k] || [])]));

    switch (type) {
        case "suite": {
            const exludedId = EXCLUDE_PREFIX + id;
            if (options?.ignore) {
                if (nextParams.suite.has(exludedId)) {
                    nextParams.suite.delete(exludedId);
                } else {
                    nextParams.suite.add(exludedId);
                }
            } else {
                clearAll();
                nextParams.suite.add(id);
            }
            break;
        }
        case "tag": {
            const exludedId = EXCLUDE_PREFIX + id;
            if (options?.ignore) {
                if (nextParams.tag.has(exludedId)) {
                    nextParams.tag.delete(exludedId);
                } else {
                    nextParams.tag.add(exludedId);
                }
            } else {
                clearAll();
                nextParams.tag.add(id);
            }
            break;
        }
        case "test": {
            const exludedId = EXCLUDE_PREFIX + id;
            if (options?.ignore) {
                if (nextParams.test.has(exludedId)) {
                    nextParams.test.delete(exludedId);
                } else {
                    nextParams.test.add(exludedId);
                }
            } else {
                clearAll();
                nextParams.test.add(id);
            }
            break;
        }
        default: {
            clearAll();
        }
    }

    for (const key in nextParams) {
        if (!nextParams[key].size) {
            nextParams[key] = null;
        }
    }

    nextParams.debugTest = options?.debug ? true : null;

    return createURL(nextParams);
}

export const EXCLUDE_PREFIX = "-";

/** @type {Partial<DEFAULT_CONFIG & DEFAULT_FILTERS>} */
export const urlParams = reactive({});

processURL();
