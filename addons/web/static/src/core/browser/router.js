/** @odoo-module **/

import { EventBus } from "@odoo/owl";
import { shallowEqual } from "../utils/objects";
import { objectToUrlEncodedString } from "../utils/urls";
import { browser } from "./browser";
import { registry } from "@web/core/registry";

export const routerBus = new EventBus();

/**
 * Casts the given string to a number if possible.
 *
 * @param {string} value
 * @returns {string|number}
 */
function cast(value) {
    return !value || isNaN(value) ? value : Number(value);
}

/**
 * @typedef {{ [key: string]: string }} Query
 * @typedef {{ [key: string]: any }} Route
 */

function parseString(str) {
    const parts = str.split("&");
    const result = {};
    for (const part of parts) {
        const [key, value] = part.split("=");
        const decoded = decodeURIComponent(value || "");
        result[key] = cast(decoded);
    }
    return result;
}

/**
 * For each push request (replaceState or pushState), filterout keys that have been locked before
 * overrides locked keys that are explicitly re-locked or unlocked
 * registers keys in "search" in "lockedKeys" according to the "lock" Boolean
 *
 * @param {Query} search An Object representing the pushed url search
 * @param {Query} currentSearch The current search compare against
 * @return {Query} The resulting "search" where previous locking has been applied
 */
function applyLocking(search, currentSearch) {
    const newSearch = Object.assign({}, search);
    for (const key in currentSearch) {
        if ([..._lockedKeys].includes(key) && !(key in newSearch)) {
            newSearch[key] = currentSearch[key];
        }
    }
    return newSearch;
}

function computeNewRoute(search, replace, currentRoute) {
    if (!replace) {
        search = Object.assign({}, currentRoute, search);
    }
    search = sanitizeSearch(search);
    if (!shallowEqual(currentRoute, search)) {
        return search;
    }
    return false;
}

function sanitize(obj, valueToRemove) {
    return Object.fromEntries(
        Object.entries(obj)
            .filter(([, v]) => v !== valueToRemove)
            .map(([k, v]) => [k, cast(v)])
    );
}

function sanitizeSearch(search) {
    return sanitize(search);
}

function sanitizeHash(hash) {
    return sanitize(hash, "");
}

/**
 * @param {string} hash
 * @returns {any}
 */
export function parseHash(hash) {
    return hash && hash !== "#" ? parseString(hash.slice(1)) : {};
}

/**
 * @param {string} search
 * @returns {any}
 */
export function parseSearchQuery(search) {
    return search ? parseString(search.slice(1)) : {};
}

/**
 * @param {{ [key: string]: any }} route
 * @returns
 */
export function routeToUrl(route) {
    let tmpRoute = Object.assign({}, route);
    let pathname = "/apps";
    const allParsers = registry.category("routeToUrl").getAll();
    for (const parser of allParsers) {
        const parsed = parser(tmpRoute);
        if (parsed) {
            tmpRoute = parsed.route;
            pathname = pathname + parsed.pathname;
            if (!parsed.continue) {
                break;
            }
        }
    }
    const search = objectToUrlEncodedString(tmpRoute);
    return pathname + (search ? "?" + search : "");
}

function getRoute(urlObj) {
    const state = parseSearchQuery(urlObj.search);
    const splitPath = urlObj.pathname.split("/").filter(Boolean);

    // If the url contains a hash, it can be for two motives:
    // 1. It is an anchor link, in that case, we ignore it, as it will not have a keys/values format
    //    the sanitizeHash function will remove it from the hash object.
    // 2. It has one or more keys/values, in that case, we merge it with the search.
    const hash = sanitizeHash(parseHash(urlObj.hash));
    if (Object.keys(hash).length > 0 || splitPath.length === 1) {
        Object.assign(state, hash);
        const url = browser.location.origin + routeToUrl(state);
        browser.history.replaceState({}, "", url);
    }
    if (splitPath.length > 1 && splitPath[0] === "apps") {
        splitPath.splice(0, 1);
        const allParsers = registry.category("getRoute").getAll();
        for (const parser of allParsers) {
            const parsed = parser(splitPath);
            if (parsed) {
                Object.assign(state, parsed.state);
                if (!parsed.continue) {
                    break;
                }
            }
        }
    }

    return state;
}

let current;
let pushTimeout;
let updateTimeout;
let allPushArgs;
let _lockedKeys;

export function startRouter() {
    current = getRoute(browser.location);
    pushTimeout = null;
    allPushArgs = [];
    _lockedKeys = new Set(["debug"]);
}

registry.category("getRoute").addEventListener("UPDATE", () => {
    browser.clearTimeout(updateTimeout);
    updateTimeout = browser.setTimeout(() => {
        current = getRoute(browser.location);
        updateTimeout = null;
    });
});

// pushState and replaceState keep the browser on the same document. It's a simulation of going to a new page.
// The back button on the browser is a navigation tool that takes you to the previous document.
// But in this case, there isn't a previous document.
// To make the back button appear to work, we need to simulate a new document being loaded.

browser.addEventListener("popstate", (ev) => {
    if (ev.state?.newURL) {
        browser.clearTimeout(pushTimeout);
        const loc = new URL(ev.state.newURL);
        current = getRoute(loc);
        routerBus.trigger("ROUTE_CHANGE");
    }
});

/**
 * @param {string} mode
 * @returns {(hash: string, options: any) => any}
 */
function makeDebouncedPush(mode) {
    function doPush() {
        // Aggregates push/replace state arguments
        const replace = allPushArgs.some(([, options]) => options && options.replace);
        let newSearch = allPushArgs.reduce((finalSearch, [search]) => {
            return Object.assign(finalSearch || {}, search);
        }, null);
        // apply Locking on the final search
        newSearch = applyLocking(newSearch, current);
        // Calculates new route based on aggregated search and options
        const newRoute = computeNewRoute(newSearch, replace, current);
        if (newRoute) {
            // If the route changed: pushes or replaces browser state
            const url = browser.location.origin + routeToUrl(newRoute);
            if (mode === "push") {
                browser.history.pushState({ newURL: url }, "", url);
            } else {
                browser.history.replaceState({ newURL: url }, "", url);
            }
            current = getRoute(browser.location);
        }
        const reload = allPushArgs.some(([, options]) => options && options.reload);
        if (reload) {
            browser.location.reload();
        }
    }
    return function pushOrReplaceState(search, options) {
        allPushArgs.push([search, options]);
        browser.clearTimeout(pushTimeout);
        pushTimeout = browser.setTimeout(() => {
            doPush();
            pushTimeout = null;
            allPushArgs = [];
        });
    };
}

startRouter();

export const router = {
    get current() {
        return current;
    },
    pushState: makeDebouncedPush("push"),
    replaceState: makeDebouncedPush("replace"),
    cancelPushes: () => browser.clearTimeout(pushTimeout),
    addLockedKey: (key) => _lockedKeys.add(key),
};

export function objectToQuery(obj) {
    const query = {};
    Object.entries(obj).forEach(([k, v]) => {
        query[k] = v ? String(v) : v;
    });
    return query;
}
