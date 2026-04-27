import { browser } from "@web/core/browser/browser";
import { parseSearchQuery, PATH_KEYS, router } from "@web/core/browser/router";
import { omit } from "@web/core/utils/objects";
import { patch } from "@web/core/utils/patch";
import { isNumeric } from "@web/core/utils/strings";
import { objectToUrlEncodedString } from "@web/core/utils/urls";

// Prefixes should be sorted by desc. length.
export const PREFIXES = ["/knowledge/article", "/knowledge/home"];

/**
 * @param {{ [key: string]: any }} state
 * @returns {string}
 */
export function stateToUrl(state) {
    let pathname;
    if (!state.resId) {
        pathname = "/knowledge/home";
    } else {
        pathname = `/knowledge/article/${state.resId}`;
    }
    const search = objectToUrlEncodedString(omit(state, "actionStack", ...PATH_KEYS));
    return `${pathname}${search ? `?${search}` : ""}`;
}

/**
 * @param {URL} urlObj
 * @returns {{ [key: string]: any }}
 */
export function urlToState(urlObj) {
    const { pathname, search } = urlObj;
    const state = parseSearchQuery(search);
    const prefix = PREFIXES.find((prefix) => pathname.startsWith(prefix));
    if (prefix === "/knowledge/article") {
        const splitPath = pathname.replace(prefix, "").split("/").toSpliced(0, 1);
        if (isNumeric(splitPath.at(0))) {
            state.resId = parseInt(splitPath.at(0));
        }
    }
    return state;
}

patch(router, {
    stateToUrl,
    urlToState,
});

// Since the patch for `stateToUrl` and `urlToState` is executed
// after the router state was already initialized, it has to be replaced.
router.replaceState(router.urlToState(new URL(browser.location)));
