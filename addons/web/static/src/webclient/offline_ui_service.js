import { browser } from "@web/core/browser/browser";
import { rpcBus } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";

export const offlineUIService = {
    dependencies: ["action", "offline"],
    async start(env, { action: actionService, offline: offlineService }) {
        const KEY = "ui-items-available-offline" + (env.debug ? "-debug" : "");
        const rawValue = browser.sessionStorage.getItem(KEY);
        const visited = rawValue ? JSON.parse(rawValue) : {};
        window.visited = visited;
        function markAsVisited() {
            console.log("MENU-SELECTED/SWITCHED-VIEW");
            const { action, view } = actionService.currentController;
            if (action.cache && view?.availableOffline && !offlineService.status.offline) {
                visited[action.id] = visited[action.id] || { views: {} };
                if (!visited[action.id].views[view.type]) {
                    visited[action.id].views[view.type] = {}; // FIXME: we'll get into RECORD-LOADED.ROOT-LOADED before anyway
                    browser.sessionStorage.setItem(KEY, JSON.stringify(visited)); // TODO: if kept in session storage, try/catch?
                }
            }
        }
        env.bus.addEventListener("ACTION_MANAGER:SWITCHED-VIEW", () => markAsVisited());
        env.bus.addEventListener("MENUS:MENU-SELECTED", () => markAsVisited());
        env.bus.addEventListener("FORM:RECORD-LOADED", ({ detail }) => {
            console.log("FORM:RECORD-LOADED", detail);
            if (detail.actionId && !offlineService.status.offline) {
                // TODO: how to check if action is cached?
                visited[detail.actionId] = visited[detail.actionId] || { views: {} };
                visited[detail.actionId].views.form = visited[detail.actionId].views.form || {};
                visited[detail.actionId].views.form[detail.resId] = true;
                browser.sessionStorage.setItem(KEY, JSON.stringify(visited)); // TODO: if kept in session storage, try/catch?
            }
        });

        function markFilterAsVisited({ actionId, query, facets, length }, viewType) {
            if (actionId && length > 0 && !offlineService.status.offline) {
                // TODO: how to check if action is cached?
                visited[actionId] = visited[actionId] || { views: {} };
                visited[actionId].views[viewType] = visited[actionId].views[viewType] || {};
                const queryStr = JSON.stringify(query);
                const count = visited[actionId].views[viewType][queryStr]?.count || 0;
                delete visited[actionId].views[viewType][queryStr]; // s.t. it is re-added at the end (last visited first)
                visited[actionId].views[viewType][queryStr] = { count: count + 1, facets };
                browser.sessionStorage.setItem(KEY, JSON.stringify(visited)); // TODO: if kept in session storage, try/catch?
            }
        }
        env.bus.addEventListener("KANBAN_VIEW:ROOT_LOADED", ({ detail }) =>
            markFilterAsVisited(detail, "kanban")
        );
        env.bus.addEventListener("LIST_VIEW:ROOT_LOADED", ({ detail }) =>
            markFilterAsVisited(detail, "list")
        );

        // alternative/other event: ACTION_MANAGER:UI-UPDATED
        // for now, we only add on MENU-SELECTED (so only if coming from a menu), but if we switch view, open a record, toggles a domain... in any action (not directly coming from a menu), we add it
        // => fix that inconsistency
        // corner case: open a view with url which isn't the default view of the app/menu => will think it can open the action but it can't
        // => cth said it's fine not to cover this case

        rpcBus.addEventListener("CLEAR-CACHES", () => {
            visited.debug = {};
            for (const key of Object.keys(visited)) {
                delete visited[key];
            }
            browser.sessionStorage.removeItem(KEY);
        });

        return { visited };
    },
};
registry.category("services").add("offline_ui", offlineUIService);
