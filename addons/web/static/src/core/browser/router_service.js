/** @odoo-module **/

import { registry } from "../registry";
import { shallowEqual } from "../utils/objects";
import { objectToUrlEncodedString } from "../utils/urls";
import { browser } from "./browser";

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
    for (let part of parts) {
        const [key, value] = part.split("=");
        const decoded = decodeURIComponent(value || "");
        result[key] = cast(decoded);
    }
    return result;
}

/**
 * For each push request (replaceState or pushState), filterout keys that have been locked before
 * overrides locked keys that are explicitly re-locked or unlocked
 * registers keys in "hash" in "lockedKeys" according to the "lock" Boolean
 *
 * @param {Set<string>} lockedKeys A set containing all keys that were locked
 * @param {Query} hash An Object representing the pushed url hash
 * @param {Query} currentHash The current hash compare against
 * @param  {Object} [options={}] Whether to lock all hash keys in "hash" to prevent them from being changed afterwards
 * @param  {Boolean} [options.lock] Whether to lock all hash keys in "hash" to prevent them from being changed afterwards
 * @return {Query} The resulting "hash" where previous locking has been applied
 */
function applyLocking(lockedKeys, hash, currentHash, options = {}) {
    const newHash = {};
    for (const key in hash) {
        if ("lock" in options) {
            options.lock ? lockedKeys.add(key) : lockedKeys.delete(key);
        } else if (lockedKeys.has(key)) {
            // forbid implicit override of key
            continue;
        }
        newHash[key] = hash[key];
    }
    for (const key in currentHash) {
        if (lockedKeys.has(key) && !(key in newHash)) {
            newHash[key] = currentHash[key];
        }
    }
    return newHash;
}

function computeNewRoute(hash, replace, currentRoute) {
    if (!replace) {
        hash = Object.assign({}, currentRoute.hash, hash);
    }
    hash = sanitizeHash(hash);
    if (!shallowEqual(currentRoute.hash, hash)) {
        return Object.assign({}, currentRoute, { hash });
    }
    return false;
}

function sanitizeHash(hash) {
    return Object.fromEntries(
        Object.entries(hash)
            .filter(([, v]) => v !== undefined)
            .map(([k, v]) => [k, cast(v)])
    );
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
    const search = objectToUrlEncodedString(route.search);
    const hash = objectToUrlEncodedString(route.hash);
    return route.pathname + (search ? "?" + search : "") + (hash ? "#" + hash : "");
}

async function redirect(env, url, wait = false) {
    if (wait) {
        await new Promise((resolve) => {
            const waitForServer = (delay) => {
                browser.setTimeout(async () => {
                    env.services
                        .rpc("/web/webclient/version_info", {})
                        .then(resolve)
                        .catch(() => waitForServer(250));
                }, delay);
            };
            waitForServer(1000);
        });
    }
    browser.location.assign(url);
}

function getRoute(urlObj) {
    const { pathname, search, hash } = urlObj;
    const searchQuery = parseSearchQuery(search);
    const hashQuery = parseHash(hash);
    return { pathname, search: searchQuery, hash: hashQuery };
}

function makeRouter(env) {
    const bus = env.bus;
    const lockedKeys = new Set();
    let current = getRoute(browser.location);
    let pushTimeout;
    browser.addEventListener("hashchange", (ev) => {
        browser.clearTimeout(pushTimeout);
        const loc = new URL(ev.newURL);
        current = getRoute(loc);
        bus.trigger("ROUTE_CHANGE");
    });

    /**
     * @param {string} mode
     * @returns {(hash: string, options: any) => any}
     */
    function makeDebouncedPush(mode) {
        let allPushArgs = [];
        function doPush() {
            // Aggregates push/replace state arguments
            const replace = allPushArgs.some(([, options]) => options && options.replace);
            const newHash = allPushArgs.reduce((finalHash, [hash, options]) => {
                hash = applyLocking(lockedKeys, hash, current.hash, options);
                if (finalHash) {
                    hash = applyLocking(lockedKeys, hash, finalHash, options);
                }
                return Object.assign(finalHash || {}, hash);
            }, null);
            // Calculates new route based on aggregated hash and options
            const newRoute = computeNewRoute(newHash, replace, current);
            if (!newRoute) {
                return;
            }
            // If the route changed: pushes or replaces browser state
            const url = browser.location.origin + routeToUrl(newRoute);
            if (mode === "push") {
                browser.history.pushState({}, "", url);
            } else {
                browser.history.replaceState({}, "", url);
            }
            current = getRoute(browser.location);
        }
        return function pushOrReplaceState(hash, options) {
            allPushArgs.push([hash, options]);
            browser.clearTimeout(pushTimeout);
            pushTimeout = browser.setTimeout(() => {
                doPush();
                pushTimeout = null;
                allPushArgs = [];
            });
        };
    }

    return {
        get current() {
            return current;
        },
        pushState: makeDebouncedPush("push"),
        replaceState: makeDebouncedPush("replace"),
        redirect: (url, wait) => redirect(env, url, wait),
        cancelPushes: () => browser.clearTimeout(pushTimeout),
    };
}

export const routerService = {
    start(env) {
        return makeRouter(env);
    },
};

export function objectToQuery(obj) {
    const query = {};
    Object.entries(obj).forEach(([k, v]) => {
        query[k] = v ? String(v) : v;
    });
    return query;
}

registry.category("services").add("router", routerService);
