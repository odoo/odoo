/**
 * OD19 Web Navigation — navigation history service
 *
 * Odoo 19 webclient pushes its router state with `{ replace: true }` on every
 * action change, so the browser history never accumulates one entry per menu.
 * Native browser back/forward therefore cannot walk menu-to-menu.
 *
 * This service keeps its own stack of router states (one entry per controller
 * mount = one entry per "page" the user sees) so that a Back/Forward button can
 * replay them through the public `action.loadState()` API.
 *
 * It also registers the Alt+← / Alt+→ shortcuts.
 */

import { reactive } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";
import { router } from "@web/core/browser/router";

const MAX_ENTRIES = 60;

/** Keys that identify a distinct "page" in the router state. */
const IDENTITY_KEYS = ["action", "model", "resId", "view_type", "active_id", "menu_id"];

function cloneState(state) {
    return JSON.parse(JSON.stringify(state));
}

function isSamePage(a, b) {
    if (!a || !b) {
        return false;
    }
    return IDENTITY_KEYS.every((key) => a[key] === b[key]);
}

/** Depth-first lookup of the first menu carrying an action, used as "app home". */
function firstActionableMenu(menu) {
    if (!menu) {
        return null;
    }
    if (menu.actionID) {
        return menu;
    }
    for (const child of menu.childrenTree || []) {
        const found = firstActionableMenu(child);
        if (found) {
            return found;
        }
    }
    return null;
}

export const od19NavHistoryService = {
    dependencies: ["action", "menu", "hotkey"],

    start(env, { action, menu, hotkey }) {
        const state = reactive({ entries: [], cursor: -1 });

        // Set while we replay an entry ourselves, so the resulting controller
        // mount is not recorded as a brand new navigation.
        let replaying = false;

        function snapshot() {
            // `router.current` is only updated after a debounced timeout (see
            // `makeDebouncedPush` in core/browser/router.js), so it still holds the
            // *previous* page when the ACTION_MANAGER:UI-UPDATED event is fired.
            // The action service writes the canonical state to sessionStorage
            // synchronously in its own `pushState()`, so we read it from there.
            let current = null;
            const stored = browser.sessionStorage.getItem("current_state");
            if (stored) {
                try {
                    current = JSON.parse(stored);
                } catch {
                    current = null;
                }
            }
            if (!current || !current.actionStack?.length) {
                current = router.current;
            }
            if (!current || !current.actionStack?.length) {
                return null;
            }
            return cloneState(current);
        }

        function record() {
            if (replaying) {
                return;
            }
            const snap = snapshot();
            if (!snap) {
                return;
            }
            const current = state.entries[state.cursor];
            if (isSamePage(current, snap)) {
                // Same page, only the search/domain changed: refresh in place.
                state.entries[state.cursor] = snap;
                return;
            }
            state.entries = state.entries.slice(0, state.cursor + 1);
            state.entries.push(snap);
            if (state.entries.length > MAX_ENTRIES) {
                state.entries.shift();
            }
            state.cursor = state.entries.length - 1;
        }

        async function goAppHome() {
            const app = menu.getCurrentApp();
            const target = app && (app.actionID ? app : firstActionableMenu(menu.getMenuAsTree(app.id)));
            if (target) {
                await menu.selectMenu(target);
            } else {
                env.bus.trigger("WEBCLIENT:LOAD_DEFAULT_APP");
            }
        }

        async function replay(index) {
            if (index < 0 || index >= state.entries.length) {
                return;
            }
            const target = cloneState(state.entries[index]);
            const previous = state.cursor;
            replaying = true;
            state.cursor = index;
            let loaded = false;
            try {
                loaded = await action.loadState(target);
            } catch (error) {
                console.warn("[od19_web_navigation] ไม่สามารถย้อนกลับได้:", error);
            } finally {
                replaying = false;
            }
            if (!loaded) {
                console.warn("[od19_web_navigation] ไม่พบหน้าที่ต้องการย้อนกลับไป");
                state.cursor = previous;
            }
        }

        async function back() {
            if (state.cursor > 0) {
                return replay(state.cursor - 1);
            }
            return goAppHome();
        }

        async function forward() {
            if (state.cursor < state.entries.length - 1) {
                return replay(state.cursor + 1);
            }
        }

        // Every controller mount triggers this event ("new" is a dialog, not a page).
        env.bus.addEventListener("ACTION_MANAGER:UI-UPDATED", (ev) => {
            if (ev.detail === "new") {
                return;
            }
            record();
        });

        hotkey.add("alt+arrowleft", () => back(), { global: true });
        hotkey.add("alt+arrowright", () => forward(), { global: true });

        return { state, back, forward };
    },
};

registry.category("services").add("od19_nav_history", od19NavHistoryService);
