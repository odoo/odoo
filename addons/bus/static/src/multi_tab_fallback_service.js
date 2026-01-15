import { browser } from "@web/core/browser/browser";
import { EventBus } from "@odoo/owl";

let multiTabId = 0;
/**
 * This service uses a Master/Slaves with Leader Election architecture in
 * order to keep track of the main tab. Tabs are synchronized thanks to the
 * localStorage.
 *
 * localStorage used keys are:
 * - multi_tab_service.lastPresenceByTab: mapping of tab ids to their last
 *   recorded presence.
 * - multi_tab_service.main: a boolean indicating whether a main tab is already
 *   present.
 * - multi_tab_service.heartbeat: last main tab heartbeat time.
 *
 * trigger:
 * - become_main_tab : when this tab became the main.
 * - no_longer_main_tab : when this tab is no longer the main.
 */
export const multiTabFallbackService = {
    start(env) {
        const bus = new EventBus();

        // CONSTANTS
        const TAB_HEARTBEAT_PERIOD = 10000; // 10 seconds
        const MAIN_TAB_HEARTBEAT_PERIOD = 1500; // 1.5 seconds
        const HEARTBEAT_OUT_OF_DATE_PERIOD = 5000; // 5 seconds
        const HEARTBEAT_KILL_OLD_PERIOD = 15000; // 15 seconds

        // PROPERTIES
        let _isOnMainTab = false;
        let lastHeartbeat = 0;
        let heartbeatTimeout;
        const now = new Date().getTime();
        const tabId = `${this.name}${multiTabId++}:${now}`;

        function startElection() {
            if (_isOnMainTab) {
                return;
            }
            // Check who's next.
            const now = new Date().getTime();
            const lastPresenceByTab =
                JSON.parse(localStorage.getItem("multi_tab_service.lastPresenceByTab")) ?? {};
            const heartbeatKillOld = now - HEARTBEAT_KILL_OLD_PERIOD;
            let newMain;
            for (const [tab, lastPresence] of Object.entries(lastPresenceByTab)) {
                // Check for dead tabs.
                if (lastPresence < heartbeatKillOld) {
                    continue;
                }
                newMain = tab;
                break;
            }
            if (newMain === tabId) {
                // We're next in queue. Electing as main.
                lastHeartbeat = now;
                localStorage.setItem("multi_tab_service.heartbeat", lastHeartbeat);
                localStorage.setItem("multi_tab_service.main", true);
                _isOnMainTab = true;
                bus.trigger("become_main_tab");
                // Removing main peer from queue.
                delete lastPresenceByTab[newMain];
                localStorage.setItem(
                    "multi_tab_service.lastPresenceByTab",
                    JSON.stringify(lastPresenceByTab)
                );
            }
        }

        function heartbeat() {
            const now = new Date().getTime();
            let heartbeatValue = parseInt(localStorage.getItem("multi_tab_service.heartbeat") ?? 0);
            const lastPresenceByTab =
                JSON.parse(localStorage.getItem("multi_tab_service.lastPresenceByTab")) ?? {};
            if (heartbeatValue + HEARTBEAT_OUT_OF_DATE_PERIOD < now) {
                // Heartbeat is out of date. Electing new main.
                startElection();
                heartbeatValue = parseInt(localStorage.getItem("multi_tab_service.heartbeat") ?? 0);
            }
            if (_isOnMainTab) {
                // Walk through all tabs and kill old ones.
                const cleanedTabs = {};
                for (const [tabId, lastPresence] of Object.entries(lastPresenceByTab)) {
                    if (lastPresence + HEARTBEAT_KILL_OLD_PERIOD > now) {
                        cleanedTabs[tabId] = lastPresence;
                    }
                }
                if (heartbeatValue !== lastHeartbeat) {
                    // Someone else is also main...
                    // It should not happen, except in some race condition situation.
                    _isOnMainTab = false;
                    lastHeartbeat = 0;
                    lastPresenceByTab[tabId] = now;
                    localStorage.setItem(
                        "multi_tab_service.lastPresenceByTab",
                        JSON.stringify(lastPresenceByTab)
                    );
                    bus.trigger("no_longer_main_tab");
                } else {
                    lastHeartbeat = now;
                    localStorage.setItem("multi_tab_service.heartbeat", now);
                    localStorage.setItem(
                        "multi_tab_service.lastPresenceByTab",
                        JSON.stringify(cleanedTabs)
                    );
                }
            } else {
                // Update own heartbeat.
                lastPresenceByTab[tabId] = now;
                localStorage.setItem(
                    "multi_tab_service.lastPresenceByTab",
                    JSON.stringify(lastPresenceByTab)
                );
            }
            const hbPeriod = _isOnMainTab ? MAIN_TAB_HEARTBEAT_PERIOD : TAB_HEARTBEAT_PERIOD;
            heartbeatTimeout = browser.setTimeout(heartbeat, hbPeriod);
        }

        function onStorage({ key, newValue }) {
            if (key === "multi_tab_service.main" && !newValue) {
                // Main was unloaded.
                startElection();
            }
        }

        /**
         * Unregister this tab from the multi-tab service. It will no longer
         * be able to become the main tab.
         */
        function unregister() {
            clearTimeout(heartbeatTimeout);
            const lastPresenceByTab =
                JSON.parse(localStorage.getItem("multi_tab_service.lastPresenceByTab")) ?? {};
            delete lastPresenceByTab[tabId];
            localStorage.setItem(
                "multi_tab_service.lastPresenceByTab",
                JSON.stringify(lastPresenceByTab)
            );

            // Unload main.
            if (_isOnMainTab) {
                _isOnMainTab = false;
                bus.trigger("no_longer_main_tab");
                browser.localStorage.removeItem("multi_tab_service.main");
            }
        }

        browser.addEventListener("pagehide", unregister);
        browser.addEventListener("storage", onStorage);

        // REGISTER THIS TAB
        const lastPresenceByTab =
            JSON.parse(localStorage.getItem("multi_tab_service.lastPresenceByTab")) ?? {};
        lastPresenceByTab[tabId] = now;
        localStorage.setItem(
            "multi_tab_service.lastPresenceByTab",
            JSON.stringify(lastPresenceByTab)
        );

        if (!localStorage.getItem("multi_tab_service.main")) {
            startElection();
        }
        heartbeat();

        return {
            bus,
            /**
             * Determine whether or not this tab is the main one.
             * it's intentionally an async function to match the API of
             * multiTabSharedWorkerService
             *
             * @returns {boolean}
             */
            async isOnMainTab() {
                return _isOnMainTab;
            },
            /**
             * Unregister this tab from the multi-tab service. It will no longer
             * be able to become the main tab.
             */
            unregister,
        };
    },
};
