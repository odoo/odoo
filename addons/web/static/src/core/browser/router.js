import { EventBus } from "@odoo/owl";
import { shallowEqual } from "../utils/objects";
import { objectToUrlEncodedString } from "../utils/urls";
import { browser } from "./browser";

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
export function stateToUrl(state) {
    const tmpState = Object.assign({}, state);
    const pathname = ["/apps"];
    if (tmpState.actionStack) {
        for (const actIndex in tmpState.actionStack) {
            const action = tmpState.actionStack[actIndex];
            if (action.resId && actIndex > 0) {
                const previousAction = tmpState.actionStack[actIndex - 1];
                if (
                    action.action === previousAction.action &&
                    action.model === previousAction.model &&
                    action.active_id === previousAction.active_id
                ) {
                    pathname.push(action.resId);
                    continue;
                }
            }
            if (action.active_id) {
                if (
                    actIndex === 0 ||
                    action.active_id !== tmpState.actionStack[actIndex - 1]?.resId
                ) {
                    pathname.push(action.active_id);
                }
            }
            if (action.action) {
                if (typeof action.action === "number" || action.action.includes(".")) {
                    pathname.push(`act-${action.action}`);
                } else {
                    pathname.push(action.action);
                }
            } else if (action.model) {
                // Note that the shourtcut don't have "."
                if (action.model.includes(".")) {
                    pathname.push(action.model);
                } else {
                    pathname.push(`m-${action.model}`);
                }
            }
            if (action.resId) {
                pathname.push(action.resId);
            }
        }
        delete tmpState.action;
        delete tmpState.active_id;
        delete tmpState.actionStack;
        if (tmpState.id) {
            pathname.pop();
            pathname.push(tmpState.id);
            delete tmpState.id;
        }
    } else {
        if (tmpState.action || tmpState.model) {
            // This is done for retro-compatibility in case of the state has only action or model and not actionStack
            if (tmpState.active_id) {
                pathname.push(tmpState.active_id);
                delete tmpState.active_id;
            }
            if (tmpState.action) {
                if (typeof tmpState.action === "number" || tmpState.action.includes(".")) {
                    pathname.push(`act-${tmpState.action}`);
                } else {
                    pathname.push(tmpState.action);
                }
                delete tmpState.action;
            } else if (tmpState.model) {
                // Note that the shourtcut don't have "."
                if (tmpState.model.includes(".")) {
                    pathname.push(tmpState.model);
                } else {
                    pathname.push(`m-${tmpState.model}`);
                }
                delete tmpState.model;
            }
            if (tmpState.resId) {
                pathname.push(tmpState.resId);
                delete tmpState.resId;
            }
        }
    }
    // Maybe we need to remove id ! (as we remove menu_id)
    const search = objectToUrlEncodedString(tmpState);
    return pathname.join("/") + (search ? "?" + search : "");
}

function urlToState(urlObj) {
    const { pathname, hash, search } = urlObj;
    const state = parseSearchQuery(search);

    // If the url contains a hash, it can be for two motives:
    // 1. It is an anchor link, in that case, we ignore it, as it will not have a keys/values format
    //    the sanitizeHash function will remove it from the hash object.
    // 2. It has one or more keys/values, in that case, we merge it with the search.
    if (pathname === "/web") {
        const sanitizedHash = sanitizeHash(parseHash(hash));
        Object.assign(state, sanitizedHash);
        const addHash = hash && !Object.keys(sanitizedHash).length;
        const url = browser.location.origin + stateToUrl(state) + (addHash ? hash : "");
        browser.history.replaceState({}, "", url);
    }

    const splitPath = pathname.split("/").filter(Boolean);

    if (splitPath.length > 1 && splitPath[0] === "apps") {
        splitPath.splice(0, 1);
        const actions = [];
        let action = {};
        let aid = undefined;
        for (const part of splitPath) {
            if (aid) {
                action.active_id = aid;
                aid = undefined;
            }
            if (isNaN(parseInt(part)) && part !== "new") {
                // part is an action (id or shortcut) or a model (when no action is found)
                if (Object.values(action).length > 0) {
                    // We have a new action, so we push the previous one
                    if (action.resId) {
                        aid = action.resId;
                    }
                    actions.push({ ...action });
                }
                action = {};
                if (part.startsWith("act-")) {
                    // it's an action id or an action xmlid
                    action.action = isNaN(parseInt(part.slice(4)))
                        ? part.slice(4)
                        : parseInt(part.slice(4));
                    continue;
                } else if (part.includes(".") || part.startsWith("m-")) {
                    // it's a model
                    // Note that the shourtcut don't have "."
                    if (part.startsWith("m-")) {
                        action.model = part.slice(2);
                    } else {
                        action.model = part;
                    }
                    continue;
                } else {
                    // it's a shortcut of an action
                    action.action = part;
                    continue;
                }
            }
            if (!isNaN(parseInt(part)) || part === "new") {
                // Action with a resId
                if (Object.values(action).length > 0) {
                    // We push the action without the id, to have a multimodel action view
                    actions.push({ ...action });
                }
                if (part === "new") {
                    action.resId = part;
                } else {
                    action.resId = parseInt(part);
                }
                continue;
            }
        }
        if (actions.length > 0 && actions[actions.length - 1].resId) {
            action.active_id = actions[actions.length - 1].resId;
        }
        actions.push(action);
        if (actions.length > 0) {
            actions.filter((a) => a.action || a.resId);
        }
        if (actions[actions.length - 1].resId && actions[actions.length - 1].resId !== "new") {
            state.id = actions[actions.length - 1].resId;
        }
        if (actions[actions.length - 1].action) {
            state.action = actions[actions.length - 1].action;
        }
        if (actions[actions.length - 1].model) {
            state.model = actions[actions.length - 1].model;
        }
        if (actions[actions.length - 1].active_id) {
            state.active_id = actions[actions.length - 1].active_id;
        }
        state.actionStack = actions;
    }

    return state;
}

let current;
let pushTimeout;
let allPushArgs;
let _lockedKeys;

export function startRouter() {
    current = urlToState(browser.location);
    pushTimeout = null;
    allPushArgs = [];
    _lockedKeys = new Set(["debug"]);
}

// pushState and replaceState keep the browser on the same document. It's a simulation of going to a new page.
// The back button on the browser is a navigation tool that takes you to the previous document.
// But in this case, there isn't a previous document.
// To make the back button appear to work, we need to simulate a new document being loaded.

browser.addEventListener("popstate", (ev) => {
    if (ev.state?.newURL) {
        browser.clearTimeout(pushTimeout);
        const loc = new URL(ev.state.newURL);
        current = urlToState(loc);
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
            const url = browser.location.origin + stateToUrl(newRoute);
            if (mode === "push") {
                browser.history.pushState({ newURL: url }, "", url);
            } else {
                browser.history.replaceState({ newURL: url }, "", url);
            }
            current = urlToState(browser.location);
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
