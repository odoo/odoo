/** @odoo-module **/

import { registry } from "@web/core/registry";
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
export const multiTabService = {
    start() {
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
        const sanitizedOrigin = location.origin.replace(/:\/{0,2}/g, "_");
        const localStoragePrefix = `${this.name}.${sanitizedOrigin}.`;
        const now = new Date().getTime();
        const tabId = `${this.name}${multiTabId++}:${now}`;

        function generateLocalStorageKey(baseKey) {
            return localStoragePrefix + baseKey;
        }

        function getItemFromStorage(key, defaultValue) {
            const item = browser.localStorage.getItem(generateLocalStorageKey(key));
            try {
                return item ? JSON.parse(item) : defaultValue;
            } catch {
                return item;
            }
        }

        function setItemInStorage(key, value) {
            browser.localStorage.setItem(generateLocalStorageKey(key), JSON.stringify(value));
        }

        function startElection() {
            if (_isOnMainTab) {
                return;
            }
            // Check who's next.
            const now = new Date().getTime();
            const lastPresenceByTab = getItemFromStorage("lastPresenceByTab", {});
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
                setItemInStorage("heartbeat", lastHeartbeat);
                setItemInStorage("main", true);
                _isOnMainTab = true;
                bus.trigger("become_main_tab");
                // Removing main peer from queue.
                delete lastPresenceByTab[newMain];
                setItemInStorage("lastPresenceByTab", lastPresenceByTab);
            }
        }

        function heartbeat() {
            const now = new Date().getTime();
            let heartbeatValue = getItemFromStorage("heartbeat", 0);
            const lastPresenceByTab = getItemFromStorage("lastPresenceByTab", {});
            if (heartbeatValue + HEARTBEAT_OUT_OF_DATE_PERIOD < now) {
                // Heartbeat is out of date. Electing new main.
                startElection();
                heartbeatValue = getItemFromStorage("heartbeat", 0);
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
                    setItemInStorage("lastPresenceByTab", lastPresenceByTab);
                    bus.trigger("no_longer_main_tab");
                } else {
                    lastHeartbeat = now;
                    setItemInStorage("heartbeat", now);
                    setItemInStorage("lastPresenceByTab", cleanedTabs);
                }
            } else {
                // Update own heartbeat.
                lastPresenceByTab[tabId] = now;
                setItemInStorage("lastPresenceByTab", lastPresenceByTab);
            }
            const hbPeriod = _isOnMainTab ? MAIN_TAB_HEARTBEAT_PERIOD : TAB_HEARTBEAT_PERIOD;
            heartbeatTimeout = browser.setTimeout(heartbeat, hbPeriod);
        }

        function onStorage({ key, newValue }) {
            if (key === generateLocalStorageKey("main") && !newValue) {
                // Main was unloaded.
                startElection();
            }
            if (PRIVATE_LOCAL_STORAGE_KEYS.includes(key)) {
                return;
            }
            if (key && key.includes(localStoragePrefix)) {
                // Only trigger the shared_value_updated event if the key is
                // related to this service/origin.
                const baseKey = key.replace(localStoragePrefix, "");
                bus.trigger("shared_value_updated", { key: baseKey, newValue });
            }
        }

        /**
         * Unregister this tab from the multi-tab service. It will no longer
         * be able to become the main tab.
         */
        function unregister() {
            clearTimeout(heartbeatTimeout);
            const lastPresenceByTab = getItemFromStorage("lastPresenceByTab", {});
            delete lastPresenceByTab[tabId];
            setItemInStorage("lastPresenceByTab", lastPresenceByTab);

            // Unload main.
            if (_isOnMainTab) {
                _isOnMainTab = false;
                bus.trigger("no_longer_main_tab");
                browser.localStorage.removeItem(generateLocalStorageKey("main"));
            }
        }

        browser.addEventListener("pagehide", unregister);
        browser.addEventListener("storage", onStorage);

        // REGISTER THIS TAB
        const lastPresenceByTab = getItemFromStorage("lastPresenceByTab", {});
        lastPresenceByTab[tabId] = now;
        setItemInStorage("lastPresenceByTab", lastPresenceByTab);

        if (!getItemFromStorage("main")) {
            startElection();
        }
        heartbeat();

        return {
            bus,
            get currentTabId() {
                return tabId;
            },
            /**
             * Determine whether or not this tab is the main one.
             *
             * @returns {boolean}
             */
            isOnMainTab() {
                return _isOnMainTab;
            },
            /**
             * Get value shared between all the tabs.
             *
             * @param {string} key
             * @param {any} defaultValue Value to be returned if this
             * key does not exist.
             */
            getSharedValue(key, defaultValue) {
                return getItemFromStorage(key, defaultValue);
            },
            /**
             * Set value shared between all the tabs.
             *
             * @param {string} key
             * @param {any} value
             */
            setSharedValue(key, value) {
                if (value === undefined) {
                    return this.removeSharedValue(key);
                }
                setItemInStorage(key, value);
            },
            /**
             * Remove value shared between all the tabs.
             *
             * @param {string} key
             */
            removeSharedValue(key) {
                browser.localStorage.removeItem(generateLocalStorageKey(key));
            },
            /**
             * Unregister this tab from the multi-tab service. It will no longer
             * be able to become the main tab.
             */
            unregister: unregister,
        };
    },
};

registry.category("services").add("multi_tab", multiTabService);
