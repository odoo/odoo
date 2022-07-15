/** @odoo-module **/

import { registry } from '@web/core/registry';
import { browser } from '@web/core/browser/browser';
import session from 'web.session';

/**
 * This class uses a Master/Slaves with Leader Election architecture in
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
 * trigger on env.bus:
 * - become_main_tab : when this tab became the main.
 * - no_longer_main_tab : when this tab is no longer the main.
 */
export class MultiTab {
    constructor(env) {
        this.env = env;

        // CONSTANTS
        this.TAB_HEARTBEAT_PERIOD = 10000; // 10 seconds
        this.MAIN_TAB_HEARTBEAT_PERIOD = 1500; // 1.5 seconds
        this.HEARTBEAT_OUT_OF_DATE_PERIOD = 5000; // 5 seconds
        this.HEARTBEAT_KILL_OLD_PERIOD = 15000; // 15 seconds
        this.LOCAL_STORAGE_PREFIX = 'multiTabService';

        // PROPERTIES
        this._isOnMainTab = false;
        this._sanitizedOrigin = session.origin.replace(/:\/{0,2}/g, '_');

        const now = new Date().getTime();
        this._id = _.uniqueId(this.LOCAL_STORAGE_PREFIX) + ':' + now;
        browser.addEventListener('unload', this._onUnload.bind(this));
        browser.addEventListener('storage', this._onStorage.bind(this));
        // REGISTER THIS TAB
        const lastPresenceByTab = this._callLocalStorage('getItem', 'lastPresenceByTab', {});
        lastPresenceByTab[this._id] = now;
        this._callLocalStorage('setItem', 'lastPresenceByTab', lastPresenceByTab);

        if (!this._callLocalStorage('getItem', 'main')) {
            this._startElection();
        }
        this._heartbeat();
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    isOnMainTab() {
        return this._isOnMainTab;
    }

    getAllTabIds() {
        return Object.keys(this._callLocalStorage('getItem', 'lastPresenceByTab', {}));
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Call browser localStorage.
     *
     * @private
     * @param {string} method (getItem, setItem, removeItem)
     * @param {string} key
     * @param {any} param
     * @returns Result of the called method, parsed.
     */
    _callLocalStorage(method, key, param) {
        if (method === 'setItem') {
            param = JSON.stringify(param);
        }
        const result = browser.localStorage[method](this._generateKey(key), param);
        if (method === 'getItem') {
            return result ? JSON.parse(result) : param;
        }
    }

    /**
     * Generates localStorage keys prefixed by LOCAL_STORAGE_PREFIX and
     * the sanitized origin, to prevent keys from conflicting when
     * several multi tab services co-exist.
     *
     * @private
     * @param {string} key
     * @returns Key prefixed with the origin.
     */
    _generateKey(key) {
        return this.LOCAL_STORAGE_PREFIX + '.' + this._sanitizedOrigin + '.' + key;
    }

    /**
     * Check all the time (according to the constants) if the tab is the main tab and
     * check if it is active. Use the local storage for this checks.
     *
     * @private
     * @see _startElection method
     */
    _heartbeat() {
        const now = new Date().getTime();
        let heartbeatValue = this._callLocalStorage('getItem', 'heartbeat', 0);
        const lastPresenceByTab = this._callLocalStorage('getItem', 'lastPresenceByTab', {});
        if (heartbeatValue + this.HEARTBEAT_OUT_OF_DATE_PERIOD < now) {
            // Heartbeat is out of date. Electing new main.
            this._startElection();
            heartbeatValue = this._callLocalStorage('getItem', 'heartbeat', 0);
        }
        if (this._isOnMainTab) {
            // Walk through all tabs and kill old ones.
            const cleanedTabs = {};
            for (const [tabId, lastPresence] of Object.entries(lastPresenceByTab)) {
                if (lastPresence + this.HEARTBEAT_KILL_OLD_PERIOD > now) {
                    cleanedTabs[tabId] = lastPresence;
                }
            }
            if (heartbeatValue !== this.lastHeartbeat) {
                // Someone else is also main...
                // It should not happen, except in some race condition situation.
                this._isOnMainTab = false;
                this.lastHeartbeat = 0;
                lastPresenceByTab[this._id] = now;
                this._callLocalStorage('setItem', 'lastPresenceByTab', lastPresenceByTab);
                this.env.bus.trigger('no_longer_main_tab');
            } else {
                this.lastHeartbeat = now;
                this._callLocalStorage('setItem', 'heartbeat', now);
                this._callLocalStorage('setItem', 'lastPresenceByTab', cleanedTabs);
            }
        } else {
            // Update own heartbeat.
            lastPresenceByTab[this._id] = now;
            this._callLocalStorage('setItem', 'lastPresenceByTab', lastPresenceByTab);
        }
        const hbPeriod = this._isOnMainTab ? this.MAIN_TAB_HEARTBEAT_PERIOD : this.TAB_HEARTBEAT_PERIOD;
        this._heartbeatTimeout = browser.setTimeout(this._heartbeat.bind(this), hbPeriod);
    }

    /**
     * Check with the local storage if the current tab is the main tab.
     * If this tab became the main, trigger 'become_main_tab' event.
     *
     * @private
     */
    _startElection() {
        if (this._isOnMainTab) {
            return;
        }
        // Check who's next.
        const now = new Date().getTime();
        const lastPresenceByTab = this._callLocalStorage('getItem', 'lastPresenceByTab', {});
        const heartbeatKillOld = now - this.HEARTBEAT_KILL_OLD_PERIOD;
        let newMain;
        for (const [tab, lastPresence] of Object.entries(lastPresenceByTab)) {
            // Check for dead tabs.
            if (lastPresence < heartbeatKillOld) {
                continue;
            }
            newMain = tab;
            break;
        }
        if (newMain === this._id) {
            // We're next in queue. Electing as main.
            this.lastHeartbeat = now;
            this._callLocalStorage('setItem', 'heartbeat', this.lastHeartbeat);
            this._callLocalStorage('setItem', 'main', true);
            this._isOnMainTab = true;
            this.env.bus.trigger('become_main_tab');
            // Removing main peer from queue.
            delete lastPresenceByTab[newMain];
            this._callLocalStorage('setItem', 'lastPresenceByTab', lastPresenceByTab);
        }
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onStorage({ key, newValue }) {
        if (key === this._generateKey('main') && !newValue) {
            // Main was unloaded.
            this._startElection();
        }
    }

    _onUnload() {
        const lastPresenceByTab = this._callLocalStorage('getItem', 'lastPresenceByTab', {});
        delete lastPresenceByTab[this._id];
        this._callLocalStorage('setItem', 'lastPresenceByTab', lastPresenceByTab);

        // Unload main.
        if (this._isOnMainTab) {
            this._callLocalStorage('removeItem', 'main');
        }
    }
}

export const multiTabService = {
    start(env) {
        return new MultiTab(env);
    },
};

registry.category('services').add('multiTab', multiTabService);
