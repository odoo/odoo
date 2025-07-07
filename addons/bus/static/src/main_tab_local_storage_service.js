import { browser } from "@web/core/browser/browser";
import { EventBus } from "@odoo/owl";

let multiTabId = 0;
/**
 * This service uses a Master/Slaves with Leader Election architecture in
 * order to keep track of the main tab. Tabs are synchronized thanks to the
 * localStorage.
 *
 * localStorage used keys are:
 * - {LOCAL_STORAGE_PREFIX}.{sanitizedOrigin}.lastPresenceByTab:
 *   mapping of tab ids to their last recorded presence.
 * - {LOCAL_STORAGE_PREFIX}.{sanitizedOrigin}.main : id of the current
 *   main tab.
 * - {LOCAL_STORAGE_PREFIX}.{sanitizedOrigin}.heartbeat : last main tab
 *   heartbeat time.
 *
 * trigger:
 * - become_main_tab : when this tab became the main.
 * - no_longer_main_tab : when this tab is no longer the main.
 * - shared_value_updated: when one of the shared values changes.
 */
export const mainTabLocalStorageService = {
    dependencies: ["multi_tab"],
    start(env, services) {
        const bus = new EventBus();

        // CONSTANTS
        const TAB_HEARTBEAT_PERIOD = 10000; // 10 seconds
        const MAIN_TAB_HEARTBEAT_PERIOD = 1500; // 1.5 seconds
        const HEARTBEAT_OUT_OF_DATE_PERIOD = 5000; // 5 seconds
        const HEARTBEAT_KILL_OLD_PERIOD = 15000; // 15 seconds
        // Keys that should not trigger the `shared_value_updated` event.
        const PRIVATE_LOCAL_STORAGE_KEYS = ["main", "heartbeat"];

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
            const lastPresenceByTab = services.multi_tab.getItemFromStorage(
                "lastPresenceByTab",
                {}
            );
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
                services.multi_tab.setItemInStorage("heartbeat", lastHeartbeat);
                services.multi_tab.setItemInStorage("main", true);
                _isOnMainTab = true;
                bus.trigger("become_main_tab");
                // Removing main peer from queue.
                delete lastPresenceByTab[newMain];
                services.multi_tab.setItemInStorage("lastPresenceByTab", lastPresenceByTab);
            }
        }

        function heartbeat() {
            const now = new Date().getTime();
            let heartbeatValue = services.multi_tab.getItemFromStorage("heartbeat", 0);
            const lastPresenceByTab = services.multi_tab.getItemFromStorage(
                "lastPresenceByTab",
                {}
            );
            if (heartbeatValue + HEARTBEAT_OUT_OF_DATE_PERIOD < now) {
                // Heartbeat is out of date. Electing new main.
                startElection();
                heartbeatValue = services.multi_tab.getItemFromStorage("heartbeat", 0);
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
                    services.multi_tab.setItemInStorage("lastPresenceByTab", lastPresenceByTab);
                    bus.trigger("no_longer_main_tab");
                } else {
                    lastHeartbeat = now;
                    services.multi_tab.setItemInStorage("heartbeat", now);
                    services.multi_tab.setItemInStorage("lastPresenceByTab", cleanedTabs);
                }
            } else {
                // Update own heartbeat.
                lastPresenceByTab[tabId] = now;
                services.multi_tab.setItemInStorage("lastPresenceByTab", lastPresenceByTab);
            }
            const hbPeriod = _isOnMainTab ? MAIN_TAB_HEARTBEAT_PERIOD : TAB_HEARTBEAT_PERIOD;
            heartbeatTimeout = browser.setTimeout(heartbeat, hbPeriod);
        }

        function onStorage({ key, newValue }) {
            if (key === services.multi_tab.generateLocalStorageKey("main") && !newValue) {
                // Main was unloaded.
                startElection();
            }
            if (PRIVATE_LOCAL_STORAGE_KEYS.includes(key)) {
                return;
            }
        }

        /**
         * Unregister this tab from the multi-tab service. It will no longer
         * be able to become the main tab.
         */
        function unregister() {
            clearTimeout(heartbeatTimeout);
            const lastPresenceByTab = services.multi_tab.getItemFromStorage(
                "lastPresenceByTab",
                {}
            );
            delete lastPresenceByTab[tabId];
            services.multi_tab.setItemInStorage("lastPresenceByTab", lastPresenceByTab);

            // Unload main.
            if (_isOnMainTab) {
                _isOnMainTab = false;
                bus.trigger("no_longer_main_tab");
                browser.localStorage.removeItem(services.multi_tab.generateLocalStorageKey("main"));
            }
        }

        browser.addEventListener("pagehide", unregister);
        browser.addEventListener("storage", onStorage);

        // REGISTER THIS TAB
        const lastPresenceByTab = services.multi_tab.getItemFromStorage("lastPresenceByTab", {});
        lastPresenceByTab[tabId] = now;
        services.multi_tab.setItemInStorage("lastPresenceByTab", lastPresenceByTab);

        if (!services.multi_tab.getItemFromStorage("main")) {
            startElection();
        }
        heartbeat();

        return {
            bus,
            /**
             * Determine whether or not this tab is the main one.
             *
             * @returns {boolean}
             */
            isOnMainTab() {
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
