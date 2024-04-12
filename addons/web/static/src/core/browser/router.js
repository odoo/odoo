import { EventBus } from "@odoo/owl";
import { omit, pick } from "../utils/objects";
import { objectToUrlEncodedString } from "../utils/urls";
import { browser } from "./browser";
import { slidingWindow } from "@web/core/utils/arrays";
import { isNumeric } from "@web/core/utils/strings";

// Keys that are serialized in the URL as path segments instead of query string
export const PATH_KEYS = ["resId", "action", "active_id", "model"];

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
 * @param {object} values An object with the values of the new state
 * @param {boolean} replace whether the values should replace the state or be
 *  layered on top of the current state
 * @returns {object} the next state of the router
 */
function computeNextState(values, replace) {
    const nextState = replace ? pick(state, ..._lockedKeys) : { ...state };
    Object.assign(nextState, values);
    // Update last entry in the actionStack
    if (nextState.actionStack?.length) {
        Object.assign(nextState.actionStack.at(-1), pick(nextState, ...PATH_KEYS));
    }
    return sanitizeSearch(nextState);
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

function pathFromActionState(state) {
    const path = [];
    const { action, model, active_id, resId } = state;
    if (active_id) {
        path.push(active_id);
    }
    if (action) {
        if (typeof action === "number" || action.includes(".")) {
            path.push(`action-${action}`);
        } else {
            path.push(action);
        }
    } else if (model) {
        if (model.includes(".")) {
            path.push(model);
        } else {
            // A few models don't have a dot at all, we need to distinguish
            // them from action paths (eg: website)
            path.push(`m-${model}`);
        }
    }
    if (resId) {
        path.push(resId);
    }
    return path.join("/");
}

/**
 * @param {{ [key: string]: any }} state
 * @returns
 */
export function stateToUrl(state) {
    let path = "";
    const actionStack = (state.actionStack || [state]).map((a) => ({ ...a }));
    if (actionStack.at(-1)?.action !== "menu") {
        for (const [prevAct, currentAct] of slidingWindow(actionStack, 2).reverse()) {
            const { action: prevAction, resId: prevResId, active_id: prevActiveId } = prevAct;
            const { action: currentAction, active_id: currentActiveId } = currentAct;
            // actions would typically map to a path like `active_id/action/res_id`
            if (currentActiveId === prevResId) {
                // avoid doubling up when the active_id is the same as the previous action's res_id
                delete currentAct.active_id;
            }
            if (prevAction === currentAction && !prevResId && currentActiveId === prevActiveId) {
                //avoid doubling up the action and the active_id when a single-record action is preceded by a multi-record action
                delete currentAct.action;
                delete currentAct.active_id;
            }
        }
        const pathSegments = actionStack.map(pathFromActionState).filter(Boolean);
        if (pathSegments.length) {
            path = `/${pathSegments.join("/")}`;
        }
    }
    const search = objectToUrlEncodedString(omit(state, "actionStack", ...PATH_KEYS));
    return `/odoo${path}${search ? `?${search}` : ""}`;
}

export function urlToState(urlObj) {
    const { pathname, hash, search } = urlObj;
    const state = parseSearchQuery(search);

    // ** url-retrocompatibility **
    // If the url contains a hash, it can be for two motives:
    // 1. It is an anchor link, in that case, we ignore it, as it will not have a keys/values format
    //    the sanitizeHash function will remove it from the hash object.
    // 2. It has one or more keys/values, in that case, we merge it with the search.
    if (pathname === "/web") {
        const sanitizedHash = sanitizeHash(parseHash(hash));
        // Old urls used "id", it is now resId for clarity. Remap to the new name.
        if (sanitizedHash.id) {
            sanitizedHash.resId = sanitizedHash.id;
            delete sanitizedHash.id;
            delete sanitizedHash.view_type;
        } else if (sanitizedHash.view_type === "form") {
            sanitizedHash.resId = "new";
            delete sanitizedHash.view_type;
        }
        Object.assign(state, sanitizedHash);
        const url = browser.location.origin + stateToUrl(state);
        // Change the url of the current history entry to the canonical url
        browser.history.replaceState(browser.history.state, null, url);
        urlObj.href = url;
    }

    const [prefix, ...splitPath] = urlObj.pathname.split("/").filter(Boolean);

    if (prefix === "odoo") {
        const actionParts = [...splitPath.entries()].filter(
            ([_, part]) => !isNumeric(part) && part !== "new"
        );
        const actions = [];
        for (const [i, part] of actionParts) {
            const action = {};
            const [left, right] = [splitPath[i - 1], splitPath[i + 1]];
            if (isNumeric(left)) {
                action.active_id = parseInt(left);
            }

            if (right === "new") {
                action.resId = "new";
            } else if (isNumeric(right)) {
                action.resId = parseInt(right);
            }

            if (part.startsWith("action-")) {
                // numeric id or xml_id
                const actionId = part.slice(7);
                action.action = isNumeric(actionId) ? parseInt(actionId) : actionId;
            } else if (part.startsWith("m-")) {
                action.model = part.slice(2);
            } else if (part.includes(".")) {
                action.model = part;
            } else {
                // action tag or path
                action.action = part;
            }

            if (action.resId && action.action) {
                actions.push(omit(action, "resId"));
            }
            // Don't create actions for models without resId unless they're the last one.
            // If the last one is a model but doesn't have a view_type, the action service will not mount it anyway.
            if (action.action || action.resId || i === splitPath.length - 1) {
                actions.push(action);
            }
        }
        const activeAction = actions.at(-1);
        if (activeAction) {
            Object.assign(state, activeAction);
            state.actionStack = actions;
        }
    }
    return state;
}

let state;
let pushTimeout;
let pushArgs;
let _lockedKeys;

export function startRouter() {
    state = urlToState(new URL(browser.location));
    pushTimeout = null;
    pushArgs = {
        replace: false,
        reload: false,
        state: {},
    };
    _lockedKeys = new Set(["debug", "lang"]);
}

/**
 * When the user navigates history using the back/forward button, the browser
 * dispatches a popstate event with the state that was in the history for the
 * corresponding history entry. We just adopt that state so that the webclient
 * can use that previous state without forcing a full page reload.
 */
browser.addEventListener("popstate", (ev) => {
    browser.clearTimeout(pushTimeout);
    state = ev.state?.nextState || {};
    // Some client actions want to handle loading their own state. This is a ugly hack to allow not
    // reloading the webclient's state when they manipulate history.
    if (!ev.state?.skipRouteChange && !router.skipLoad) {
        routerBus.trigger("ROUTE_CHANGE");
    }
    router.skipLoad = false;
});

/**
 * When clicking internal links, do a loadState instead of a full page reload.
 * This also alows the mobile app to not open an in-app browser for them.
 */
browser.addEventListener("click", (ev) => {
    if (ev.defaultPrevented || ev.target.closest("[contenteditable]")) {
        return;
    }
    const href = ev.target.closest("a")?.getAttribute("href");
    if (href && href !== "#") {
        let url;
        try {
            url = new URL(href, browser.location.origin);
        } catch {
            return;
        }
        if (
            browser.location.origin === url.origin &&
            browser.location.pathname.startsWith("/odoo") &&
            (["/web", "/odoo"].includes(url.pathname) || url.pathname.startsWith("/odoo/"))
        ) {
            ev.preventDefault();
            const state = urlToState(url);
            router.pushState(state, { replace: true });
            new Promise((res) => setTimeout(res, 0)).then(() => routerBus.trigger("ROUTE_CHANGE"));
        }
    }
});

/**
 * @param {string} mode
 */
function makeDebouncedPush(mode) {
    function doPush() {
        // Calculates new route based on aggregated search and options
        const nextState = computeNextState(pushArgs.state, pushArgs.replace);
        const url = browser.location.origin + stateToUrl(nextState);
        if (url !== browser.location.href) {
            // If the route changed: pushes or replaces browser state
            if (mode === "push") {
                // Because doPush is delayed, the history entry will have the wrong name.
                // We set the document title to what it was at the time of the pushState
                // call, then push, which generates the history entry with the right title
                // then restore the title to what it's supposed to be
                const originalTitle = document.title;
                document.title = pushArgs.title;
                browser.history.pushState({ nextState }, "", url);
                document.title = originalTitle;
            } else {
                browser.history.replaceState({ nextState }, "", url);
            }
            state = nextState;
        }
        if (pushArgs.reload) {
            browser.location.reload();
        }
    }
    /**
     * @param {object} state
     * @param {object} options
     */
    return function pushOrReplaceState(state, options = {}) {
        pushArgs.replace ||= options.replace;
        pushArgs.reload ||= options.reload;
        pushArgs.title = document.title;
        Object.assign(pushArgs.state, state);
        browser.clearTimeout(pushTimeout);
        pushTimeout = browser.setTimeout(() => {
            doPush();
            pushTimeout = null;
            pushArgs = {
                replace: false,
                reload: false,
                state: {},
            };
        });
    };
}

startRouter();

export const router = {
    get current() {
        return state;
    },
    // TODO: stop debouncing these and remove the ugly hack to have the correct title for history entries
    pushState: makeDebouncedPush("push"),
    replaceState: makeDebouncedPush("replace"),
    cancelPushes: () => browser.clearTimeout(pushTimeout),
    addLockedKey: (key) => _lockedKeys.add(key),
    skipLoad: false,
};

export function objectToQuery(obj) {
    const query = {};
    Object.entries(obj).forEach(([k, v]) => {
        query[k] = v ? String(v) : v;
    });
    return query;
}
