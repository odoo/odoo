import { EventBus } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { user } from "@web/core/user";

/**
 * State of the apps sidebar (see @web/webclient/apps_sidebar/apps_sidebar).
 *
 * It is stored in the local storage, per user, s.t. the sidebar keeps its
 * configuration from one session to another. Components displaying that state
 * must subscribe to `appsSidebarBus` to be notified when it changes.
 */

export const appsSidebarBus = new EventBus();

const DEFAULT_STATE = {
    // whether the sidebar is displayed next to the action manager
    isVisible: false,
    // whether the sidebar displays the app names next to their icon
    isExpanded: false,
    // xmlids of the apps to display, all of them if empty
    pinnedApps: [],
};

// The state is always exposed through the same object, s.t. components keeping
// a reference on it always read up-to-date values.
const state = { ...DEFAULT_STATE };

function getStorageKey() {
    return `web.apps_sidebar.${user.userId}`;
}

/**
 * @returns {typeof DEFAULT_STATE} the current state, which must not be mutated
 *  directly (use the functions below instead)
 */
export function getAppsSidebarState() {
    let storedState = null;
    try {
        storedState = JSON.parse(browser.localStorage.getItem(getStorageKey()));
    } catch {
        // the stored state is corrupted => fallback on the default one
    }
    Object.assign(state, DEFAULT_STATE, storedState);
    if (!Array.isArray(state.pinnedApps)) {
        state.pinnedApps = [];
    }
    return state;
}

function updateState(changes) {
    Object.assign(getAppsSidebarState(), changes);
    browser.localStorage.setItem(getStorageKey(), JSON.stringify(state));
    appsSidebarBus.trigger("UPDATE");
}

export function toggleAppsSidebar() {
    updateState({ isVisible: !getAppsSidebarState().isVisible });
}

export function toggleAppsSidebarExpanded() {
    updateState({ isExpanded: !getAppsSidebarState().isExpanded });
}

/**
 * Adds or removes an app from the pinned ones. When there's no pinned app, the
 * sidebar displays all apps.
 *
 * @param {string} xmlid the xmlid of the app's menu
 */
export function toggleAppsSidebarPin(xmlid) {
    const pinnedApps = getAppsSidebarState().pinnedApps;
    if (pinnedApps.includes(xmlid)) {
        updateState({ pinnedApps: pinnedApps.filter((appXmlid) => appXmlid !== xmlid) });
    } else {
        updateState({ pinnedApps: [...pinnedApps, xmlid] });
    }
}
