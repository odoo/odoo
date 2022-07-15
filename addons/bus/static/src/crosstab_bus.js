/** @odoo-module **/

import { browser } from '@web/core/browser/browser';
import session from 'web.session';

import { Longpolling } from '@bus/longpolling_bus';

/**
 * CrossTab
 *
 * This is an extension of the longpolling bus with browser cross-tab synchronization.
 * It uses the multiTab service.
 * - only the main tab handles longpolling.
 * - tabs are synchronized by means of the local storage.
 *
 * localStorage used keys are:
 * - {LOCAL_STORAGE_PREFIX}.{sanitizedOrigin}.channels : shared public channel list to listen during the poll
 * - {LOCAL_STORAGE_PREFIX}.{sanitizedOrigin}.options : shared options
 * - {LOCAL_STORAGE_PREFIX}.{sanitizedOrigin}.notification : the received notifications from the last poll
 *
 * trigger:
 * - notification : when a notification is receive from the long polling
 */
export class CrossTab extends Longpolling {
    constructor(env, services) {
        super(env, services);
        this.LOCAL_STORAGE_PREFIX = 'bus';

        // properties
        this._isRegistered = false;

        var now = new Date().getTime();
        // used to prefix localStorage keys
        this._sanitizedOrigin = session.origin.replace(/:\/{0,2}/g, '_');
        this._currentTabChannels = new Set();
        // prevents collisions between different tabs and in tests
        this._id = _.uniqueId(this.LOCAL_STORAGE_PREFIX) + ':' + now;
        if (this._callLocalStorage('getItem', 'last_ts', 0) + 50000 < now) {
            this._callLocalStorage('removeItem', 'last');
        }
        this._lastNotificationID = this._callLocalStorage('getItem', 'last', 0);
        this._registerWindowUnload();
        browser.addEventListener('storage', this._onStorage.bind(this));

        env.bus.addEventListener('no_longer_main_tab', () => this.stopPolling());
        env.bus.addEventListener('become_main_tab', () => this.startPolling());
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Share the bus channels with the others tab by the local storage
     *
     * @override
     */
    addChannel(channel) {
        this._currentTabChannels.add(channel);
        super.addChannel(channel);
        this._updateChannels();
    }

    /**
     * Share the bus channels with the others tab by the local storage
     *
     * @override
     */
    deleteChannel(channel) {
        this._currentTabChannels.delete(channel);
        super.deleteChannel(channel);
        this._updateChannels();
    }

    /**
     * @return {string}
     */
    getTabId() {
        return this._id;
    }

    /**
     * Use the local storage to share the long polling from the master tab.
     *
     * @override
     */
    startPolling() {
        if (!this._isRegistered) {
            this._isRegistered = true;

            if (this.env.services['multiTab'].isOnMainTab()) {
                this._callLocalStorage('setItem', 'options', this._options);
            } else {
                this._options = this._callLocalStorage('getItem', 'options', this._options);
            }
            this._updateChannels();
        }

        if (this.env.services['multiTab'].isOnMainTab()) {
            super.startPolling();
        }
    }

    /**
     * Share the option with the local storage
     *
     * @override
     */
    updateOption(key, value) {
        super.updateOption(key, value);
        this._callLocalStorage('setItem', 'options', this._options);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Call browser localStorage.
     *
     * @private
     * @param {string} method (getItem, setItem, removeItem, on)
     * @param {string} key
     * @param {any} param
     * @returns service information
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
     * Generates localStorage keys prefixed by bus. (LOCAL_STORAGE_PREFIX = the name
     * of this addon), and the sanitized origin, to prevent keys from
     * conflicting when several bus instances (polling different origins)
     * co-exist.
     *
     * @private
     * @param {string} key
     * @returns key prefixed with the origin
     */
    _generateKey(key) {
        return this.LOCAL_STORAGE_PREFIX + '.' + this._sanitizedOrigin + '.' + key;
    }

    /**
     * @private
     */
    _registerWindowUnload() {
        browser.addEventListener('unload', this._onUnload.bind(this));
    }

    /**
     * Update localstorage channels of with the channels of this tab.
     *
     * @private
     * @return {boolean} true if the aggregated channels has changed.
     */
    _updateChannels() {
        const currentPeerIds = new Set(this.env.services['multiTab'].getAllTabIds());
        const peerChannels = this._callLocalStorage('getItem', 'channels')  || {};
        const peerChannelsBefore = JSON.stringify(peerChannels);
        peerChannels[this._id] = Array.from(this._currentTabChannels);

        // Clean outdated channels.
        for (const channelPeerId of Object.keys(peerChannels)) {
            if (!currentPeerIds.has(channelPeerId)) {
                delete peerChannels[channelPeerId];
            }
        }

        const peerChannelsAfter = JSON.stringify(peerChannels);
        if (peerChannelsBefore === peerChannelsAfter) {
            return false;
        }
        this._callLocalStorage('setItem', 'channels', peerChannels);

        const allChannels = new Set();
        for (const channels of Object.values(peerChannels)) {
            for (const channel of channels) {
                allChannels.add(channel);
            }
        }
        // Insure the current tab channels are always in the aggregated channels
        // in case this tab is not in the currentPeerIds nor peerChannels.
        for (const channel of this._currentTabChannels) {
            allChannels.add(channel);
        }
        this._channels = Array.from(allChannels);
        return true;
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * If it's the master tab, the notifications ares broadcasted to other tabs by the
     * local storage.
     *
     * @override
     */
    _onPoll(notifications) {
        var notifs = super._onPoll(notifications);
        if (this.env.services['multiTab'].isOnMainTab() && notifs.length) {
            this._callLocalStorage('setItem', 'last', this._lastNotificationID);
            this._callLocalStorage('setItem', 'last_ts', new Date().getTime());
            this._callLocalStorage('setItem', 'notification', notifs);
        }
    }

    /**
     * Handler when the local storage is updated
     *
     * @private
     * @param {OdooEvent} event
     * @param {string} event.key
     * @param {string} event.newValue
     */
    _onStorage(e) {
        if (!e.key || !e.key.includes(this.LOCAL_STORAGE_PREFIX)) {
            return;
        }
        var value = JSON.parse(e.newValue);
        var key = e.key;

        // last notification id changed
        if (key === this._generateKey('last')) {
            this._lastNotificationID = value || 0;
        }
        // notifications changed
        else if (key === this._generateKey('notification')) {
            if (!this.env.services['multiTab'].isOnMainTab()) {
                this.trigger("notification", value);
            }
        }
        // update channels
        else if (key === this._generateKey('channels')) {
            if (this._updateChannels()) {
                this._restartPolling();
            };
        }
        // update options
        else if (key === this._generateKey('options')) {
            this._options = value;
        }
    }

    /**
     * Handler when unload the window
     *
     * @private
     */
    _onUnload() {
        this._currentTabChannels.clear();
        this._updateChannels();
    }
}
