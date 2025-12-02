import { browser } from "@web/core/browser/browser";
import { rpcBus } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";

export const offlineUIService = {
    dependencies: ["action"],
    async start(env, { action: actionService }) {
        const KEY = "ui-items-available-offline" + (env.debug ? "-debug" : "");
        const rawValue = browser.sessionStorage.getItem(KEY);
        const visited = rawValue ? JSON.parse(rawValue) : {};

        function markAsVisited() {
            const { action, view } = actionService.currentController;
            if (action.cache && view?.availableOffline) {
                visited[action.id] = visited[action.id] || { views: {} };
                if (!visited[action.id].views[view.type]) {
                    visited[action.id].views[view.type] = view.type === "form" ? {} : true; // FIXME: we'll get into RECORD-LOADED before anyway
                    browser.sessionStorage.setItem(KEY, JSON.stringify(visited)); // TODO: if kept in session storage, try/catch?
                }
            }
        }
        env.bus.addEventListener("ACTION_MANAGER:SWITCHED-VIEW", () => markAsVisited());
        env.bus.addEventListener("MENUS:MENU-SELECTED", () => markAsVisited());
        env.bus.addEventListener("FORM:RECORD-LOADED", ({ detail }) => {
            if (detail.actionId) {
                visited[detail.actionId] = visited[detail.actionId] || { views: {} };
                visited[detail.actionId].views.form = visited[detail.actionId].views.form || {};
                visited[detail.actionId].views.form[detail.resId] = true;
                browser.sessionStorage.setItem(KEY, JSON.stringify(visited)); // TODO: if kept in session storage, try/catch?
            }
        });
        // alternative/other event: ACTION_MANAGER:UI-UPDATED
        // corner case: open a view with url which isn't the default view of the app/menu => will think it can open the action but it can't

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
