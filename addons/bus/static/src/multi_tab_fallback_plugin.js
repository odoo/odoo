import { browser } from "@web/core/browser/browser";
import { EventBus, Plugin, useListener } from "@odoo/owl";

let multiTabId = 0;
/**
 * This plugin uses a Master/Slaves with Leader Election architecture in
 * order to keep track of the main tab. Tabs are synchronized thanks to the
 * localStorage.
 *
 * localStorage used keys are:
 * - multi_tab_plugin.lastPresenceByTab: mapping of tab ids to their last
 *   recorded presence.
 * - multi_tab_plugin.main: a boolean indicating whether a main tab is already
 *   present.
 * - multi_tab_plugin.heartbeat: last main tab heartbeat time.
 *
 * trigger:
 * - become_main_tab : when this tab became the main.
 * - no_longer_main_tab : when this tab is no longer the main.
 */
export class MultiTabFallbackPlugin extends Plugin {
    bus = new EventBus();

    // CONSTANTS
    static TAB_HEARTBEAT_PERIOD = 10000; // 10 seconds
    static MAIN_TAB_HEARTBEAT_PERIOD = 1500; // 1.5 seconds
    static HEARTBEAT_OUT_OF_DATE_PERIOD = 5000; // 5 seconds
    static HEARTBEAT_KILL_OLD_PERIOD = 15000; // 15 seconds

    // PROPERTIES
    /** @private */
    _isOnMainTab = false;
    /** @private */
    lastHeartbeat = 0;
    /** @private */
    heartbeatTimeout;
    /** @private */
    now = null;
    /** @private */
    tabId = null;

    setup() {
        this.now = new Date().getTime();
        this.tabId = `${this.name}${multiTabId++}:${this.now}`;

        useListener(browser, "pagehide", () => this.unregister());
        useListener(browser, "storage", (ev) => this.onStorage(ev));

        // REGISTER THIS TAB
        const lastPresenceByTab =
            JSON.parse(localStorage.getItem("multi_tab_service.lastPresenceByTab")) ?? {};
        lastPresenceByTab[this.tabId] = this.now;
        localStorage.setItem(
            "multi_tab_service.lastPresenceByTab",
            JSON.stringify(lastPresenceByTab)
        );

        if (!localStorage.getItem("multi_tab_service.main")) {
            this.startElection();
        }
        this.heartbeat();
    }

    /**
     * Determine whether or not this tab is the main one.
     * it's intentionally an async function to match the API of
     * multiTabSharedWorkerService
     *
     * @returns {boolean}
     */
    async isOnMainTab() {
        return this._isOnMainTab;
    }

    /**
     * @private
     */
    startElection() {
        if (this._isOnMainTab) {
            return;
        }
        // Check who's next.
        const now = new Date().getTime();
        const lastPresenceByTab =
            JSON.parse(localStorage.getItem("multi_tab_service.lastPresenceByTab")) ?? {};
        const heartbeatKillOld = now - MultiTabFallbackPlugin.HEARTBEAT_KILL_OLD_PERIOD;
        let newMain;
        for (const [tab, lastPresence] of Object.entries(lastPresenceByTab)) {
            // Check for dead tabs.
            if (lastPresence < heartbeatKillOld) {
                continue;
            }
            newMain = tab;
            break;
        }
        if (newMain === this.tabId) {
            // We're next in queue. Electing as main.
            this.lastHeartbeat = now;
            localStorage.setItem("multi_tab_service.heartbeat", this.lastHeartbeat);
            localStorage.setItem("multi_tab_service.main", true);
            this._isOnMainTab = true;
            this.bus.trigger("become_main_tab");
            // Removing main peer from queue.
            delete lastPresenceByTab[newMain];
            localStorage.setItem(
                "multi_tab_service.lastPresenceByTab",
                JSON.stringify(lastPresenceByTab)
            );
        }
    }

    heartbeat() {
        const now = new Date().getTime();
        let heartbeatValue = parseInt(localStorage.getItem("multi_tab_service.heartbeat") ?? 0);
        const lastPresenceByTab =
            JSON.parse(localStorage.getItem("multi_tab_service.lastPresenceByTab")) ?? {};
        if (heartbeatValue + MultiTabFallbackPlugin.HEARTBEAT_OUT_OF_DATE_PERIOD < now) {
            // Heartbeat is out of date. Electing new main.
            this.startElection();
            heartbeatValue = parseInt(localStorage.getItem("multi_tab_service.heartbeat") ?? 0);
        }
        if (this._isOnMainTab) {
            // Walk through all tabs and kill old ones.
            const cleanedTabs = {};
            for (const [tabId, lastPresence] of Object.entries(lastPresenceByTab)) {
                if (lastPresence + MultiTabFallbackPlugin.HEARTBEAT_KILL_OLD_PERIOD > now) {
                    cleanedTabs[tabId] = lastPresence;
                }
            }
            if (heartbeatValue !== this.lastHeartbeat) {
                // Someone else is also main...
                // It should not happen, except in some race condition situation.
                this._isOnMainTab = false;
                this.lastHeartbeat = 0;
                lastPresenceByTab[this.tabId] = now;
                localStorage.setItem(
                    "multi_tab_service.lastPresenceByTab",
                    JSON.stringify(lastPresenceByTab)
                );
                this.bus.trigger("no_longer_main_tab");
            } else {
                this.lastHeartbeat = now;
                localStorage.setItem("multi_tab_service.heartbeat", this.now);
                localStorage.setItem(
                    "multi_tab_service.lastPresenceByTab",
                    JSON.stringify(cleanedTabs)
                );
            }
        } else {
            // Update own heartbeat.
            lastPresenceByTab[this.tabId] = now;
            localStorage.setItem(
                "multi_tab_service.lastPresenceByTab",
                JSON.stringify(lastPresenceByTab)
            );
        }
        const hbPeriod = this._isOnMainTab
            ? MultiTabFallbackPlugin.MAIN_TAB_HEARTBEAT_PERIOD
            : MultiTabFallbackPlugin.TAB_HEARTBEAT_PERIOD;
        this.heartbeatTimeout = browser.setTimeout(() => this.heartbeat(), hbPeriod);
    }

    onStorage({ key, newValue }) {
        if (key === "multi_tab_service.main" && !newValue) {
            // Main was unloaded.
            this.startElection();
        }
    }

    /**
     * Unregister this tab from the multi-tab service. It will no longer
     * be able to become the main tab.
     */
    unregister() {
        clearTimeout(this.heartbeatTimeout);
        const lastPresenceByTab =
            JSON.parse(localStorage.getItem("multi_tab_service.lastPresenceByTab")) ?? {};
        delete lastPresenceByTab[this.tabId];
        localStorage.setItem(
            "multi_tab_service.lastPresenceByTab",
            JSON.stringify(lastPresenceByTab)
        );

        // Unload main.
        if (this._isOnMainTab) {
            this._isOnMainTab = false;
            this.bus.trigger("no_longer_main_tab");
            browser.localStorage.removeItem("multi_tab_service.main");
        }
    }
}
